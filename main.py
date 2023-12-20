import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import os
import platform

cred = credentials.Certificate("cred.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def clear_console():
    system = platform.system()
    if system == 'Windows':
        os.system('cls')
    elif system == 'Linux' or system == 'Darwin':
        os.system('clear')


class TrainingTracker:
    def __init__(self):
        self.current_playlist = None
        self.current_task = None
        self.df = pd.DataFrame(columns=["Date", "Playlist", "Task", "Score", "Sensitivity", "Repetitions"])

    def choose_playlist(self):
        playlists = self.get_playlists()
        print("Available playlists:")
        for idx, playlist in enumerate(playlists, start=1):
            print(f"{idx}. Name: {playlist['name']}, Tasks: {', '.join(playlist['tasks'])}")
        choice = int(input("Choose playlist (enter index): "))
        self.current_playlist = playlists[choice - 1]

    def create_playlist(self):
        playlist_name = input("Enter playlist name: ")
        playlist_tasks = input("Enter playlist tasks (comma-separated): ").split(",")

        for task_name in playlist_tasks:
            while True:
                try:
                    highscore = int(input(f"Enter initial high score for task {task_name}: "))
                    if highscore <= 0:
                        raise ValueError("High score must be a positive integer.")
                    break
                except ValueError:
                    print("Invalid input. Please enter a valid positive integer for the initial high score.")

            threshold = 0.95 * highscore
            task_data = {
                "highscore": highscore,
                "threshold": threshold,
                "scores": [],
            }
            db.collection("tasks").document(f"{playlist_name}_{task_name}").set(task_data)

        playlist_data = {"name": playlist_name, "tasks": playlist_tasks}
        db.collection("playlists").add(playlist_data)
        print("Playlist created successfully.")

    def edit_playlist(self):
        playlists = self.get_playlists()
        print("Available playlists:")
        for idx, playlist in enumerate(playlists, start=1):
            print(f"{idx}. Name: {playlist['name']}, Tasks: {', '.join(playlist['tasks'])}")
        choice = int(input("Choose playlist to edit (enter index): "))
        playlist_id = playlists[choice - 1].id

        new_name = input("Enter new playlist name (leave empty to keep the current name): ")
        new_tasks = input("Enter new playlist tasks (comma-separated, leave empty to keep the current tasks): ")

        updated_data = {}
        if new_name:
            updated_data["name"] = new_name
        if new_tasks:
            new_task_list = new_tasks.split(",")

            current_tasks = playlists[choice - 1]['tasks']

            tasks_added = set(new_task_list) - set(current_tasks)
            tasks_modified = set(current_tasks) - set(new_task_list)

            for added_task in tasks_added:
                highscore = int(input(f"Enter initial high score for task {added_task}: "))
                threshold = 0.95 * highscore
                task_data = {
                    "highscore": highscore,
                    "threshold": threshold,
                    "scores": [],
                }
                db.collection("tasks").document(f"{new_name}_{added_task}").set(task_data)

            for modified_task in tasks_modified:
                new_highscore = int(input(f"Enter new initial high score for task {modified_task}: "))
                threshold = 0.95 * new_highscore
                db.collection("tasks").document(f"{new_name}_{modified_task}").update({
                    "highscore": new_highscore,
                    "threshold": threshold,
                })

            updated_data["tasks"] = new_task_list

        db.collection("playlists").document(playlist_id).update(updated_data)
        print("Playlist edited successfully.")

    def delete_playlist(self):
        playlists = self.get_playlists()
        print("Available playlists:")
        for idx, playlist in enumerate(playlists, start=1):
            print(f"{idx}. Name: {playlist['name']}, Tasks: {', '.join(playlist['tasks'])}")
        choice = int(input("Choose playlist to delete (enter index): "))
        playlist_snapshot = db.collection("playlists").get()[choice - 1]
        playlist_id = playlist_snapshot.id
        db.collection("playlists").document(playlist_id).delete()
        print("Playlist and associated tasks deleted successfully.")

    def view_playlists(self):
        playlists = self.get_playlists()
        print("Available playlists:")
        for idx, playlist in enumerate(playlists, start=1):
            print(f"{idx}. Name: {playlist['name']}, Tasks: {', '.join(playlist['tasks'])}")

    def get_playlists(self):
        playlists = db.collection("playlists").get()
        return [playlist.to_dict() for playlist in playlists]

    def view_tasks(self):
        if self.current_playlist:
            playlist_name = self.current_playlist['name']
            tasks = db.collection("tasks").get()
            print(f"Tasks for {playlist_name} playlist:")
            for task_name in self.current_playlist['tasks']:
                task_ref = db.collection("tasks").document(f"{playlist_name}_{task_name}")
                task_data = task_ref.get().to_dict()
                if task_data:
                    print(f"Name: {task_name}, Highscore: {task_data.get('highscore', 'N/A')}, "
                          f"Avg Last 10: {task_data.get('avg_last_10', 'N/A')}, "
                          f"Threshold: {task_data.get('threshold', 'N/A')}, "
                          f"cm/360: {task_data.get('sensitivity', 'N/A')}")
                else:
                    print(f"No data available for task: {task_name}")
        else:
            print("No playlist selected. Please choose a playlist first.")

    def view_all_tasks(self):
        tasks = db.collection("tasks").get()
        print("All tasks with highscores:")
        for task in tasks:
            task_data = task.to_dict()
            print(f"Task: {task.id}, Highscore: {task_data.get('highscore', 'N/A')}")

    def update_data(self):
        if self.current_playlist:
            task_name = input("Enter task name: ")

            while True:
                try:
                    sensitivity = float(input("Enter sensitivity: "))
                    if sensitivity < 0:
                        raise ValueError("Sensitivity must be a positive number.")
                    break
                except ValueError:
                    print("Invalid input. Please enter a valid positive number for sensitivity.")

            while True:
                try:
                    repetitions = int(input("Enter repetitions: "))
                    if repetitions <= 0:
                        raise ValueError("Repetitions must be a positive integer.")
                    break
                except ValueError:
                    print("Invalid input. Please enter a valid positive integer for repetitions.")

            scores = []

            for i in range(repetitions):
                while True:
                    try:
                        score = int(input(f"Enter score for repetition {i + 1}: "))
                        break
                    except ValueError:
                        print("Invalid input. Please enter a valid integer for the score.")

                scores.append(score)

            self.update_scores(task_name, scores, sensitivity)

        else:
            print("No playlist selected. Please choose a playlist first.")

    def update_scores(self, task_name, new_scores, sensitivity):
        if self.current_playlist:
            playlist_name = self.current_playlist["name"]
            task_ref = db.collection("tasks").document(f"{playlist_name}_{task_name}")
            task_data = task_ref.get()

            if task_data.exists:
                task_data = task_data.to_dict()
                current_scores = task_data.get("scores", [])
                date_today = datetime.today().strftime('%Y-%m-%d')

                updated_scores = current_scores + [{"score": score, "date": date_today} for score in new_scores]

                highscore = max(updated_scores)
                avg_last_10 = round(sum(updated_scores[-10:]) / min(10, len(updated_scores)), 2)
                threshold = 0.95 * highscore

                task_data = {
                    "sensitivity": sensitivity,
                    "highscore": highscore,
                    "avg_last_10": avg_last_10,
                    "threshold": threshold,
                }

                task_ref.set(task_data, merge=True)
            else:
                print(f"No data found for task: {task_name}")
        else:
            print("No playlist selected. Please choose a playlist first.")

    def refresh(self):
        tasks = db.collection("tasks").get()

        for task in tasks:
            task_data = task.to_dict()
            current_scores = task_data.get("scores", [])

            if current_scores:
                avg_last_10 = round(sum(current_scores[-10:]) / min(10, len(current_scores)), 2)
                highscore = max(current_scores)
                threshold = 0.95 * highscore

                task_ref = db.collection("tasks").document(task.id)
                task_ref.set({"avg_last_10": avg_last_10, "highscore": highscore, "threshold": threshold}, merge=True)

        print("Data refreshed successfully.")

    def delete_all_tasks(self):
        confirmation = input("Are you sure you want to delete all tasks? (y/n): ")
        if confirmation.lower() == 'y':
            tasks = db.collection("tasks").get()
            for task in tasks:
                task.reference.delete()
            print("All tasks deleted successfully.")
        else:
            print("Task deletion aborted.")

    def delete_task_by_name(self, task_name):
        confirmation = input(f"Are you sure you want to delete the task '{task_name}'? (y/n): ")
        if confirmation.lower() == 'y':
            playlist_name = self.current_playlist['name'] if self.current_playlist else None
            task_ref = db.collection("tasks").document(f"{playlist_name}_{task_name}")
            task_data = task_ref.get()
            if task_data.exists:
                task_ref.delete()
                print(f"Task '{task_name}' deleted successfully.")
            else:
                print(f"No data found for task: {task_name}")
        else:
            print("Task deletion aborted.")

    def view_data(self, time_period):
        playlists = self.get_playlists()

        if not playlists:
            print("No playlists available. Please create a playlist first.")
            return

        for playlist in playlists:
            playlist_name = playlist['name']
            playlist_tasks = playlist['tasks']

            print(f"\nPlaylist: {playlist_name}")
            print("\n{:<20} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15}".format(
                "Task", "Highscore", "New Highscore", "Avg Last 10", "Avg Today", "Threshold Achieved", "Sensitivity"
            ))

            for task_name in playlist_tasks:
                task_ref = db.collection("tasks").document(f"{playlist_name}_{task_name}")
                task_data = task_ref.get().to_dict()

                if task_data:
                    task_id = f"{playlist_name}_{task_name}"
                    highscore = task_data.get('highscore', 'N/A')
                    new_highscore = task_data.get('new_highscore', 'N/A')
                    avg_last_10 = task_data.get('avg_last_10', 'N/A')
                    avg_today = self.calculate_avg_for_period(task_data.get('scores', []), time_period)
                    threshold_achieved = task_data.get('threshold_achieved', 'N/A')
                    sensitivity = task_data.get('sensitivity', 'N/A')

                    print("{:<20} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15}".format(
                        task_id, highscore, new_highscore, avg_last_10, avg_today, threshold_achieved, sensitivity
                    ))

                else:
                    print(f"No data available for task: {task_name}")

    def calculate_avg_for_period(self, scores, time_period):
        today = datetime.today()
        if time_period == 'day':
            start_date = today
        elif time_period == 'week':
            start_date = today - timedelta(days=today.weekday())
        elif time_period == 'month':
            start_date = today.replace(day=1)
        elif time_period == 'year':
            start_date = today.replace(month=1, day=1)
        else:
            return 'N/A'

        relevant_scores = [score['score'] for score in scores if
                           datetime.strptime(score['date'], '%Y-%m-%d') >= start_date]
        return round(sum(relevant_scores) / len(relevant_scores), 2) if relevant_scores else 'N/A'


if __name__ == "__main__":
    tracker = TrainingTracker()

    while True:
        clear_console()
        tracker.view_tasks()
        print("\n1. Playlists\n2. Tasks\n3. View Data\n4. Refresh\n0. Exit")
        choice = input("Enter choice: ")

        if choice == '1':
            while True:
                clear_console()
                print("\n1. Choose Playlist\n2. Create Playlist\n3. Edit Playlist\n4. Delete Playlist\n5. View Playlists\n0. Exit")
                choice = input("Enter choice: ")
                if choice == '1':
                    tracker.choose_playlist()
                elif choice == '2':
                    tracker.create_playlist()
                elif choice == '3':
                    tracker.edit_playlist()
                elif choice == '4':
                    tracker.delete_playlist()
                elif choice == '5':
                    tracker.view_playlists()
                elif choice == '0':
                    break
                else:
                    print("Invalid choice. Please try again.")
        elif choice == '2':
            while True:
                clear_console()
                tracker.view_tasks()
                print("\n1. Update data\n2. View tasks for current playlist\n3. View all tasks\n4. Delete all tasks\n5. Delete task by name\n0. Exit")
                choice = input("Enter choice: ")
                if choice == '1':
                    tracker.update_data()
                elif choice == '2':
                    tracker.view_tasks()
                elif choice == '3':
                    tracker.view_all_tasks()
                elif choice == '4':
                    tracker.delete_all_tasks()
                elif choice == '5':
                    task_name = input("Enter the task name to delete: ")
                    tracker.delete_task_by_name(task_name)
                elif choice == '0':
                    break
                else:
                    print("Invalid choice. Please try again.")
        elif choice == '3':
            while True:
                clear_console()
                print("\n1. View day\n2. View week\n3. View monthly\n4. View yearly\n5. View all\n0. Exit")
                choice = input("Enter choice: ")
                if choice == '1':
                    tracker.view_data("day")
                elif choice == '2':
                    tracker.view_data("week")
                elif choice == '3':
                    tracker.view_data("month")
                elif choice == '4':
                    tracker.view_data("year")
                elif choice == '5':
                    tracker.view_data("all")
                elif choice == '0':
                    break
                else:
                    print("Invalid choice. Please try again.")
        elif choice == '4':
            tracker.refresh()
        elif choice == '0':
            break
        else:
            print("Invalid choice. Please try again.")
