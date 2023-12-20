import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os

cred = credentials.Certificate("cred.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


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
            updated_data["tasks"] = new_tasks.split(",")
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

        for task_name in playlist_snapshot.to_dict().get("tasks", []):
            db.collection("tasks").document(task_name).delete()

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
            print(f"Tasks for {self.current_playlist['name']} playlist:")
            for task_name in self.current_playlist['tasks']:
                task_ref = db.collection("tasks").document(task_name)
                task_data = task_ref.get().to_dict()
                if task_data:
                    print(f"Name: {task_name}, Highscore: {task_data.get('highscore', 'N/A')}, "
                          f"Avg Last 10: {task_data.get('avg_last_10', 'N/A')}, "
                          f"Threshold: {task_data.get('threshold', 'N/A')}")
                else:
                    print(f"No data available for task: {task_name}")
        else:
            print("No playlist selected. Please choose a playlist first.")

    def update_data(self):
        if self.current_playlist:
            task_name = input("Enter task name: ")
            sensitivity = float(input("Enter sensitivity: "))
            repetitions = int(input("Enter repetitions: "))
            scores = []

            for i in range(repetitions):
                score = int(input(f"Enter score for repetition {i + 1}: "))
                scores.append(score)

            self.update_scores(task_name, scores, sensitivity)

        else:
            print("No playlist selected. Please choose a playlist first.")

    def update_scores(self, task_name, new_scores, sensitivity):
        if self.current_playlist:
            task_ref = db.collection("tasks").document(task_name)
            task_data = task_ref.get()

            if task_data.exists:
                task_data = task_data.to_dict()
                current_scores = task_data.get("scores", [])
                updated_scores = current_scores + new_scores

                highscore = max(updated_scores)
                avg_last_10 = sum(updated_scores[-10:]) / min(10, len(updated_scores))
                threshold = 0.95 * highscore

                task_data = {
                    "sensitivity": sensitivity,
                    "scores": updated_scores,
                    "highscore": highscore,
                    "avg_last_10": avg_last_10,
                    "threshold": threshold,
                }

                task_ref.set(task_data, merge=True)
            else:
                print(f"No data found for task: {task_name}")
        else:
            print("No playlist selected. Please choose a playlist first.")

    def view_data(self, time_period):
        # TODO: Implement viewing data for the specified time period
        pass


if __name__ == "__main__":
    tracker = TrainingTracker()

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        tracker.view_tasks()
        print("\n1. Playlists\n2. Select Task\n3. View Data\n0. Exit")
        choice = input("Enter choice: ")

        if choice == '1':
            while True:
                os.system('cls' if os.name == 'nt' else 'clear')
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
                os.system('cls' if os.name == 'nt' else 'clear')
                print("\n1. Update data\n0. Exit")
                choice = input("Enter choice: ")
                if choice == '1':
                    tracker.update_data()
                elif choice == '0':
                    break
                else:
                    print("Invalid choice. Please try again.")
        elif choice == '3':
            while True:
                os.system('cls' if os.name == 'nt' else 'clear')
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
        elif choice == '0':
            break
        else:
            print("Invalid choice. Please try again.")
