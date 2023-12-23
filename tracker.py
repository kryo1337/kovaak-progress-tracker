import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import ArrayUnion
from datetime import datetime, timedelta
import os
import platform
import warnings

cred = credentials.Certificate("cred.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


def clear_console():
    system = platform.system()
    if system == 'Windows':
        os.system('cls')
    elif system == 'Linux' or system == 'Darwin':
        os.system('clear')


class Tracker:
    def __init__(self):
        self.current_playlist = None
        self.current_task = None
        self.df = pd.DataFrame(columns=["Date", "Tasks", "Scores", "Sensitivity", "Repetitions", "Old_Highscore", "Highscore", "Avg_Daily", "Avg_10", "Threshold", "Threshold_Achieved"])

    def create_task(self):
        task_name = input("Enter task name: ")

        while True:
            try:
                highscore = int(input(f"Enter initial highscore for task {task_name}: "))
                if highscore <= 0:
                    raise ValueError("Highscore must be a positive integer.")
                break
            except ValueError:
                print("Invalid input. Please enter a valid positive integer for the initial highscore.")

        threshold = round(0.9 * highscore, 2)

        task_data = {
            "Date": "",
            "Tasks": task_name,
            "Scores": [],
            "Sensitivity": None,
            "Repetitions": 0,
            "Old_Highscore": None,
            "Highscore": highscore,
            "Avg_Daily": None,
            "Avg_10": None,
            "Threshold": threshold,
            "Threshold_Achieved": None
        }

        db.collection("tasks").document(task_name).set(task_data)
        print(f"Task '{task_name}' created successfully.")

    def edit_task(self, task_name):
        while True:
            try:
                new_highscore = int(input(f"Enter new highscore for task {task_name}: "))
                if new_highscore <= 0:
                    raise ValueError("Highscore must be a positive integer.")
                break
            except ValueError:
                print("Invalid input. Please enter a valid positive integer for the new highscore.")

        new_threshold = round(0.95 * new_highscore, 2)

        db.collection("tasks").document(task_name).update({
            "Highscore": new_highscore,
            "Threshold": new_threshold,
        })
        print(f"Task '{task_name}' edited successfully.")

    def delete_task(self, task_name):
        task_ref = db.collection("tasks").document(task_name)
        if task_ref.get().exists:
            task_ref.delete()
            print(f"Task '{task_name}' deleted successfully.")
        else:
            print(f"Task '{task_name}' does not exist.")

    def delete_all_tasks(self):
        tasks = db.collection("tasks").get()
        for task in tasks:
            db.collection("tasks").document(task.id).delete()
        print("All tasks deleted successfully.")

    def view_all_tasks(self):
        tasks = db.collection("tasks").get()
        if not tasks:
            print("No tasks found.")
        else:
            print("All Tasks:")
            for task in tasks:
                task_name = task.id
                print(f"- {task_name}")

    def get_all_tasks(self):
        tasks = db.collection("tasks").get()
        return [task.id for task in tasks]

    def create_playlist(self):
        playlist_name = input("Enter playlist name: ")

        all_tasks = self.get_all_tasks()
        self.view_all_tasks()

        selected_tasks_input = input("Enter task names (comma-separated) for the playlist: ")
        selected_tasks = [task.strip() for task in selected_tasks_input.split(',') if task.strip() in all_tasks]

        playlist_data = {"playlist_name": playlist_name, "tasks": selected_tasks}
        db.collection("playlists").document(playlist_name).set(playlist_data)
        print(f"Playlist '{playlist_name}' created successfully with tasks: {', '.join(selected_tasks)}.")

    def edit_playlist(self, playlist_name):
        new_playlist_name = input(
            f"Enter new name for playlist {playlist_name} (press Enter to keep the current name): ")

        existing_playlist = db.collection("playlists").document(playlist_name).get()
        if existing_playlist.exists:
            existing_tasks = existing_playlist.to_dict().get("tasks", [])
        else:
            existing_tasks = []

        if new_playlist_name.strip():
            db.collection("playlists").document(new_playlist_name).set({"tasks": existing_tasks})
            print(f"Playlist '{new_playlist_name}' created successfully.")

            playlist_ref = db.collection("playlists").document(playlist_name)
            if playlist_ref.get().exists:
                playlist_ref.delete()
                print(f"Old playlist '{playlist_name}' deleted successfully.")
            else:
                print(f"Old playlist '{playlist_name}' does not exist.")
        else:
            print(f"Playlist name remains unchanged.")

        self.view_all_tasks()
        selected_tasks_input = input(
            "Enter updated task names (comma-separated) for the playlist or press Enter to skip: ")
        selected_tasks = [task.strip() for task in selected_tasks_input.split(',') if
                          task.strip() in self.df["Tasks"].unique()]

        selected_tasks = selected_tasks or existing_tasks

        db.collection("playlists").document(new_playlist_name).update({"tasks": selected_tasks})
        print(f"Playlist '{new_playlist_name}' edited successfully with updated tasks: {', '.join(selected_tasks)}.")

    def delete_playlist(self, playlist_name):
        playlist_ref = db.collection("playlists").document(playlist_name)
        if playlist_ref.get().exists:
            playlist_ref.delete()
            print(f"Playlist '{playlist_name}' deleted successfully.")
        else:
            print(f"Playlist '{playlist_name}' does not exist.")

    def delete_all_playlists(self):
        playlists = db.collection("playlists").get()
        for playlist in playlists:
            db.collection("playlists").document(playlist.id).delete()
        print("All playlists deleted successfully.")

    def view_playlists(self):
        playlists = db.collection("playlists").get()
        if not playlists:
            print("No playlists found.")
        else:
            print("All Playlists:")
            for playlist in playlists:
                playlist_data = playlist.to_dict()
                playlist_name = playlist.id
                tasks = playlist_data.get("tasks", [])
                tasks_str = ", ".join(tasks) if tasks else "No tasks"
                print(f"- {playlist_name}: {tasks_str}")

    def view_tasks_playlist(self, playlist_name):
        playlist_ref = db.collection("playlists").document(playlist_name)
        playlist_data = playlist_ref.get().to_dict()
        if playlist_data:
            tasks = playlist_data.get("tasks", [])
            print(f"Tasks in Playlist '{playlist_name}': {', '.join(tasks)}")
        else:
            print(f"Playlist '{playlist_name}' does not exist.")

    def choose_playlist(self):
        playlists = db.collection("playlists").get()
        if not playlists:
            print("No playlists found.")
            return

        print("Select a playlist:")
        for idx, playlist in enumerate(playlists):
            playlist_name = playlist.id
            print(f"{idx + 1}. {playlist_name}")

        try:
            selected_index = int(input("Enter the number of the playlist: ")) - 1
            selected_playlist = playlists[selected_index]
            playlist_name = selected_playlist.id
            self.current_playlist = playlist_name
            print(f"Playlist '{playlist_name}' selected.")
        except (ValueError, IndexError):
            print("Invalid input. Please select a valid playlist.")

    def choose_task(self):
        if not self.current_playlist:
            print("Error: Please choose a playlist first.")
            return

        playlist_ref = db.collection("playlists").document(self.current_playlist)
        playlist_data = playlist_ref.get().to_dict()

        if playlist_data:
            tasks = playlist_data.get("tasks", [])
            if tasks:
                print("Select a task from the playlist:")
                for idx, task in enumerate(tasks):
                    print(f"{idx + 1}. {task}")

                try:
                    selected_index = int(input("Enter the number of the task: ")) - 1
                    selected_task = tasks[selected_index]
                    self.current_task = selected_task
                    print(f"Task '{selected_task}' selected.")
                except (ValueError, IndexError):
                    print("Invalid input. Please select a valid task.")
            else:
                print(f"No tasks found in the playlist '{self.current_playlist}'.")
        else:
            print(f"Playlist '{self.current_playlist}' does not exist.")

    def update_task(self):
        if not self.current_task:
            print("Error: Please choose a task first.")
            return

        sensitivity = float(input("Enter sensitivity: "))
        repetitions = int(input("Enter the number of repetitions: "))

        scores = []
        for rep in range(repetitions):
            score = int(input(f"Enter score for repetition {rep + 1}: "))
            scores.append(score)

        date_today = datetime.now().strftime("%Y-%m-%d")

        existing_entry = self.df[
            (self.df["Tasks"].str.lower() == self.current_task.lower()) &
            (self.df["Date"] == date_today.lower())
            ]

        if not existing_entry.empty:
            repetitions += existing_entry["Repetitions"].values[0]
            scores += existing_entry["Scores"].values[0]

        task_ref = db.collection("tasks").document(self.current_task)
        existing_task_data = task_ref.get().to_dict()

        old_highscore = existing_task_data.get("Highscore", 0)

        print(old_highscore)

        highscore = max(scores)
        avg_daily = sum(scores) / repetitions
        avg_10 = sum(scores[-10:]) / min(10, repetitions)

        if old_highscore != 0:
            threshold = round(0.9 * old_highscore, 2)
        else:
            threshold = round(0.9 * highscore, 2)
        print(threshold)
        threshold_achieved = highscore >= threshold if threshold else None

        task_data = {
            "Date": date_today,
            "Tasks": self.current_task,
            "Scores": scores,
            "Sensitivity": sensitivity,
            "Repetitions": repetitions,
            "Old_Highscore": old_highscore,
            "Highscore": highscore,
            "Avg_Daily": avg_daily,
            "Avg_10": avg_10,
            "Threshold": threshold,
            "Threshold_Achieved": threshold_achieved
        }

        task_index = self.df.index[
            (self.df["Tasks"].str.lower() == self.current_task.lower()) &
            (self.df["Date"] == date_today.lower())
            ].tolist()

        if task_index:
            task_index = task_index[0]
            for key, value in task_data.items():
                self.df.at[task_index, key] = value

        task_ref = db.collection("tasks").document(self.current_task)
        existing_task_data = task_ref.get().to_dict()

        if existing_task_data:
            existing_scores = existing_task_data.get("Scores", [])
            existing_repetitions = existing_task_data.get("Repetitions", 0)

            updated_scores = existing_scores + scores
            updated_repetitions = existing_repetitions + repetitions

            updated_task_data = {
                "Date": date_today,
                "Tasks": self.current_task,
                "Scores": updated_scores,
                "Sensitivity": sensitivity,
                "Repetitions": updated_repetitions,
                "Old_Highscore": old_highscore if highscore > old_highscore else None,
                "Highscore": highscore,
                "Avg_Daily": avg_daily,
                "Avg_10": avg_10,
                "Threshold": threshold,
                "Threshold_Achieved": threshold_achieved
            }

            task_ref.update(updated_task_data)

        print("Task data updated successfully.")

    def view_task_data(self):
        if not self.current_task:
            print("Error: Please choose a task first.")
            return

        db = firestore.client()
        task_ref = db.collection("tasks").document(self.current_task)
        task_data = task_ref.get().to_dict()

        if task_data:
            print("\nTask Data:")

            fields_order = ["Date", "Tasks", "Sensitivity", "Repetitions", "Old_Highscore", "Highscore", "Avg_Daily",
                            "Avg_10", "Threshold", "Threshold_Achieved"]

            date_format = "{:<20}"
            headers = [date_format.format("Date")] + ["{:<15}".format(header) for header in fields_order[1:] if
                                                      header != "Scores"]
            print(" ".join(headers))
            date_str = date_format.format(task_data["Date"])
            data_str = " ".join(
                ["{:<15}".format(str(task_data[header])) for header in fields_order[1:] if header != "Scores"])
            print(date_str + " " + data_str)
        else:
            print(f"No data found for the task '{self.current_task}'.")


if __name__ == "__main__":
    tracker = Tracker()

    while True:
        print("\n1. Playlists\n2. Tasks\n3. Update\n4. View\n5. Refresh\n0. Exit")
        main_choice = input("Enter choice: ")

        if main_choice == '1':
            while True:
                print(
                    "\n1. Create playlist\n2. Edit playlist\n3. View playlist\n4. Delete playlist\n5. Delete all playlists\n0. Exit")
                playlist_choice = input("Enter choice: ")
                if playlist_choice == '1':
                    tracker.create_playlist()
                elif playlist_choice == '2':
                    playlist_name = input("Enter the playlist name to edit: ")
                    tracker.edit_playlist(playlist_name)
                elif playlist_choice == '3':
                    tracker.view_playlists()
                elif playlist_choice == '4':
                    playlist_name = input("Enter the playlist name to delete: ")
                    tracker.delete_playlist(playlist_name)
                elif playlist_choice == '5':
                    tracker.delete_all_playlists()
                elif playlist_choice == '0':
                    break
                else:
                    print("Invalid choice. Please try again.")
        elif main_choice == '2':
            while True:
                print(
                    "\n1. Create task\n2. Edit task\n3. View tasks in playlist\n4. View all tasks\n5. Delete task by name\n6. Delete all tasks\n0. Exit")
                task_choice = input("Enter choice: ")
                if task_choice == '1':
                    tracker.create_task()
                elif task_choice == '2':
                    task_name = input("Enter the task name to edit: ")
                    tracker.edit_task(task_name)
                elif task_choice == '3':
                    playlist_name = input("Enter the playlist name: ")
                    tracker.view_tasks_playlist(playlist_name)
                elif task_choice == '4':
                    tracker.view_all_tasks()
                elif task_choice == '5':
                    task_name = input("Enter the task name to delete: ")
                    tracker.delete_task(task_name)
                elif task_choice == '6':
                    tracker.delete_all_tasks()
                elif task_choice == '0':
                    break
                else:
                    print("Invalid choice. Please try again.")
        if main_choice == '3':
            while True:
                print("\n1. Choose playlist\n2. Choose task\n3. Update task\n4. View task data\n0. Exit")
                update_choice = input("Enter choice: ")
                if update_choice == '1':
                    tracker.choose_playlist()
                elif update_choice == '2':
                    tracker.choose_task()
                elif update_choice == '3':
                    tracker.update_task()
                elif update_choice == '4':
                    tracker.view_task_data()
                elif update_choice == '0':
                    break
                else:
                    print("Invalid choice. Please try again.")
        elif main_choice == '4':
            while True:
                print("\n1. View day\n2. View week\n3. View monthly\n4. View yearly\n5. View all\n0. Exit")
                view_choice = input("Enter choice: ")
                if view_choice == '1':
                    tracker.view_data("day")
                elif view_choice == '2':
                    tracker.view_data("week")
                elif view_choice == '3':
                    tracker.view_data("month")
                elif view_choice == '4':
                    tracker.view_data("year")
                elif view_choice == '5':
                    tracker.view_data("all")
                elif view_choice == '0':
                    break
                else:
                    print("Invalid choice. Please try again.")
        elif main_choice == '5':
            tracker.refresh()
        elif main_choice == '0':
            break
        else:
            print("Invalid choice. Please try again.")
