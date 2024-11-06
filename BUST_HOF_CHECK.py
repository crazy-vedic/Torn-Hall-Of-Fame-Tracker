import requests
import csv
import datetime
import os
import json
import matplotlib.pyplot as plt

# Function to check if the script already ran today based on log file
def last_run_date(log_file):
    if os.path.exists(log_file):
        with open(log_file, "r") as file:
            reader = list(csv.reader(file))
            if len(reader) > 1:  # Check if there's at least one data row
                last_entry = reader[-1][0]
                last_run_timestamp = datetime.datetime.strptime(last_entry, '%d-%m-%Y %H:%M')
                # If the date has not changed since the last log, exit the script
                if last_run_timestamp.date() == datetime.datetime.now().date():
                    print(f"Script has already run today for {log_file}. Exiting.")
                    return False
    return True

# Fetch data from the API
def fetch_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

# Extract the relevant stats from user data
def get_user_stats(user_data):
    busts_value = user_data["hof"]["busts"]["value"]
    busts_rank = user_data["hof"]["busts"]["rank"]
    return busts_value, busts_rank

# Extract required busts for a given position (dynamic position based on JSON input)
def get_position_busts(hof_data, goal_ranking):
    for position_data in hof_data["hof"]:
        if position_data["rank"] == goal_ranking:
            return position_data["value"]
    return None

# Log the data into the specified log file
def log_data(log_file, current_rank, bust_count, busts_needed):
    with open(log_file, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.datetime.now().strftime('%d-%m-%Y %H:%M'), current_rank, bust_count, busts_needed])

# Plot the progress
def plot_progress(log_file, goal_ranking, webhook_url):
    dates = []
    bust_counts = []
    targets = []

    with open(log_file, "r") as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            date = datetime.datetime.strptime(row[0], '%d-%m-%Y %H:%M')
            dates.append(date)
            bust_counts.append(int(row[2]))
            targets.append(int(row[3]))

    plt.figure(figsize=(10, 6))
    plt.plot(dates, bust_counts, label="Bust Count")
    plt.plot(dates, targets, 'r--', label=f"Target (Position {goal_ranking})")
    plt.xlabel("Date")
    plt.ylabel("People Busted")
    plt.title(f"Bust Progress for Position {goal_ranking} Over Time")
    plt.legend()
    plt.grid()

    plot_filename = "temp.png"
    plt.savefig(plot_filename)
    plt.close()  # Close the plot to release resources

    # Send the plot to Discord
    send_to_discord(plot_filename, webhook_url)

    # Delete the temporary plot file
    if os.path.exists(plot_filename):
        os.remove(plot_filename)

# Send the generated plot to Discord
def send_to_discord(image_file, webhook_url):
    with open(image_file, 'rb') as f:
        files = {
            'file': (image_file, f, 'image/png')
        }
        data = {
            'content': '<@609728408112332811>'  # Mention the user in the message
        }
        response = requests.post(webhook_url, data=data, files=files)
        if response.status_code == 200:
            print("Successfully sent the plot to Discord!")
        else:
            print(f"Failed to send the plot. Status code: {response.status_code}, Response: {response.text}")

# Main function to process the data for each user
def process_user_data():
    # Read input JSON file
    with open('checkers.json', 'r') as f:
        users = json.load(f)

    WRITE=False
    for user in users:
        log_file = f"logs/{user_id}_{user_cat}_{goal_ranking}.csv"
        if not last_run_date(log_file):
            continue
        # Check and create log file if it doesn't exist
        user_id = user['userID']
        user_cat = user['userCat']
        goal_ranking = user['goalRanking']
        webhook_url = user['webhookUrl']

        if not WRITE and "logFile" not in user:
            WRITE=True

        # Fetch user data and HoF data
        user_data = fetch_data(f"https://api.torn.com/v2/user/?selections=hof&key={user['userKey']}&id={user_id}")
        hof_data = fetch_data(f"https://api.torn.com/v2/torn/?selections=hof&key={user['userKey']}&limit=1&offset={goal_ranking-1}&cat={user_cat}")

        # Get user stats and required busts
        busts_value, current_rank = get_user_stats(user_data)
        required_busts = get_position_busts(hof_data, goal_ranking)

        if required_busts is None:
            print(f"Goal ranking {goal_ranking} not found in the Hall of Fame.")
            continue

        # Calculate busts needed to reach goal ranking
        busts_needed = required_busts - busts_value
        print(f"Current rank: {current_rank}, Busts: {busts_value}")
        print(f"Busts needed to reach goal ranking {goal_ranking}: {busts_needed}")
        # Log the data
        log_data(log_file, current_rank, busts_value, busts_needed)
        plot_progress(log_file, goal_ranking, webhook_url)
    if WRITE:
        with open('checkers.json','w') as f:
            json.dump(users, f, indent=4)


# Run the main process
if __name__ == "__main__":
    # Ensure the logs directory exists
    if not os.path.exists("logs"):
        os.makedirs("logs")

    process_user_data()
