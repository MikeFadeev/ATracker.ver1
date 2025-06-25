import flet as ft
from datetime import datetime, timedelta
import json
import os
import asyncio

class Task:
    def __init__(self, name, project=None, tags=None, life_area=None):
        self.name = name
        self.project = project
        self.tags = tags if tags else []
        self.life_area = life_area
        self.is_active = False
        self.start_time = None
        self.total_time = timedelta()
        self.daily_time = {}

    def toggle_active(self):
        self.is_active = not self.is_active
        if self.is_active:
            self.start_time = datetime.now()
        else:
            if self.start_time:
                elapsed = datetime.now() - self.start_time
                self.total_time += elapsed
                self.record_daily_time(elapsed)
                self.start_time = None

    def record_daily_time(self, elapsed):
        today = datetime.now().date().isoformat()
        if today in self.daily_time:
            self.daily_time[today] += elapsed
        else:
            self.daily_time[today] = elapsed

    def get_current_time(self):
        if self.is_active and self.start_time:
            return self.total_time + (datetime.now() - self.start_time)
        return self.total_time

class TimeTrackerApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Time Tracker"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window_width = 800
        self.page.window_height = 600
        
        self.tasks = []
        self.projects = []
        self.tags = []
        self.life_areas = []
        
        self.active_task = None
        self.load_data()
        self.setup_ui()
        self.page.run_task(self.daily_checker)
        #self.check_new_day()

    def setup_ui(self):
        # Create controls
        self.task_name_input = ft.TextField(label="Task Name", expand=True)
        self.project_dropdown = ft.Dropdown(label="Project", options=[], expand=True)
        self.tag_chips = ft.Row(wrap=True)
        self.life_area_dropdown = ft.Dropdown(label="Life Area", options=[], expand=True)
        
        self.task_list = ft.ListView(expand=True)
        self.stats_view = ft.Column()
        
        # Buttons
        add_task_btn = ft.ElevatedButton("Add Task", on_click=self.add_task)
        manage_projects_btn = ft.ElevatedButton("Manage Projects", on_click=self.manage_projects)
        manage_tags_btn = ft.ElevatedButton("Manage Tags", on_click=self.manage_tags)
        manage_life_areas_btn = ft.ElevatedButton("Manage Life Areas", on_click=self.manage_life_areas)
        
        # Tabs
        self.tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="Tasks", content=self.task_list),
                ft.Tab(text="Statistics", content=self.stats_view),
            ],
            expand=True,
        )
        
        # Layout
        self.page.add(
            ft.Column([
                ft.Row([
                    self.task_name_input,
                    self.project_dropdown,
                    self.life_area_dropdown,
                ]),
                ft.Text("Tags:"),
                self.tag_chips,
                ft.Row([
                    add_task_btn,
                    manage_projects_btn,
                    manage_tags_btn,
                    manage_life_areas_btn,
                ]),
                self.tabs,
            ], expand=True)
        )
        
        self.update_ui()

    def update_ui(self):
        # Update dropdowns
        self.project_dropdown.options = [
            ft.dropdown.Option(text=p) for p in self.projects
        ]
        self.project_dropdown.options.insert(0, ft.dropdown.Option(text="None"))
        
        self.life_area_dropdown.options = [
            ft.dropdown.Option(text=la) for la in self.life_areas
        ]
        self.life_area_dropdown.options.insert(0, ft.dropdown.Option(text="None"))
        
        # Update tag chips
        self.tag_chips.controls = []
        for tag in self.tags:
            chip = ft.Chip(
                label=ft.Text(tag),
                on_select=lambda e, t=tag: self.toggle_task_tag(t),
            )
            self.tag_chips.controls.append(chip)
        
        # Update task list
        self.task_list.controls = []
        for task in self.tasks:
            time_spent = task.get_current_time()
            hours, remainder = divmod(time_spent.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            task_card = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.TIMER if task.is_active else ft.Icons.TIMER_OUTLINED),
                            title=ft.Text(task.name),
                            subtitle=ft.Text(f"Project: {task.project or 'None'}\n"
                                           f"Tags: {', '.join(task.tags) or 'None'}\n"
                                           f"Life Area: {task.life_area or 'None'}"),
                        ),
                        ft.Text(f"Time spent: {hours:02d}:{minutes:02d}:{seconds:02d}"),
                    ]),
                    padding=10,
                    on_click=lambda e, t=task: self.toggle_task(t),
                ),
                elevation=5,
                color=ft.Colors.BLUE if task.is_active else None,
            )
            self.task_list.controls.append(task_card)
        
        self.page.update()

    def toggle_task(self, task):
        if self.active_task and self.active_task != task and self.active_task.is_active:
            self.active_task.toggle_active()
        
        task.toggle_active()
        self.active_task = task if task.is_active else None
        self.update_ui()

    def toggle_task_tag(self, tag):
        # This would be implemented to toggle tags for a selected task
        pass

    def add_task(self, e):
        name = self.task_name_input.value.strip()
        if not name:
            return
        
        project = self.project_dropdown.value if self.project_dropdown.value != "None" else None
        life_area = self.life_area_dropdown.value if self.life_area_dropdown.value != "None" else None
        
        # Get selected tags (implementation needed)
        selected_tags = []
        
        task = Task(name, project, selected_tags, life_area)
        self.tasks.append(task)
        self.task_name_input.value = ""
        self.update_ui()
        self.save_data()

    def manage_projects(self, e):
        def save_projects(e):
            self.projects = [p.strip() for p in projects_input.value.split(",") if p.strip()]
            self.save_data()
            self.update_ui()
            self.page.close_dialog()
        
        projects_input = ft.TextField(
            label="Projects (comma separated)",
            value=", ".join(self.projects)
        )
        
        self.page.dialog = ft.AlertDialog(
            title=ft.Text("Manage Projects"),
            content=projects_input,
            actions=[
                ft.ElevatedButton("Save", on_click=save_projects),
                ft.ElevatedButton("Cancel", on_click=lambda e: self.page.close_dialog()),
            ],
            open=True,
        )
        self.page.update()

    def manage_tags(self, e):
        def save_tags(e):
            self.tags = [t.strip() for t in tags_input.value.split(",") if t.strip()]
            self.save_data()
            self.update_ui()
            self.page.close_dialog()
        
        tags_input = ft.TextField(
            label="Tags (comma separated)",
            value=", ".join(self.tags)
        )
        
        self.page.dialog = ft.AlertDialog(
            title=ft.Text("Manage Tags"),
            content=tags_input,
            actions=[
                ft.ElevatedButton("Save", on_click=save_tags),
                ft.ElevatedButton("Cancel", on_click=lambda e: self.page.close_dialog()),
            ],
            open=True,
        )
        self.page.update()

    def manage_life_areas(self, e):
        def save_life_areas(e):
            self.life_areas = [la.strip() for la in life_areas_input.value.split(",") if la.strip()]
            self.save_data()
            self.update_ui()
            self.page.close_dialog()
        
        life_areas_input = ft.TextField(
            label="Life Areas (comma separated)",
            value=", ".join(self.life_areas)
        )
        
        self.page.dialog = ft.AlertDialog(
            title=ft.Text("Manage Life Areas"),
            content=life_areas_input,
            actions=[
                ft.ElevatedButton("Save", on_click=save_life_areas),
                ft.ElevatedButton("Cancel", on_click=lambda e: self.page.close_dialog()),
            ],
            open=True,
        )
        self.page.update()
    async def daily_checker(self):
        while True:
            self.check_new_day()
            await asyncio.sleep(60)  # Проверяем каждую минуту

    def check_new_day(self):
        # Проверяем, наступил ли новый день, и сбрасываем дневные таймеры
        today = datetime.now().date()
        for task in self.tasks:
            if task.daily_time:
                last_date = max(task.daily_time.keys())
                if last_date != today.isoformat():
                    task.daily_time = {}
        
        self.update_ui()

    def save_data(self):
        data = {
            "tasks": [
                {
                    "name": task.name,
                    "project": task.project,
                    "tags": task.tags,
                    "life_area": task.life_area,
                    "total_time": task.total_time.total_seconds(),
                    "daily_time": {k: v.total_seconds() for k, v in task.daily_time.items()}
                } for task in self.tasks
            ],
            "projects": self.projects,
            "tags": self.tags,
            "life_areas": self.life_areas,
        }
        
        with open("time_tracker_data.json", "w") as f:
            json.dump(data, f)

    def load_data(self):
        if os.path.exists("time_tracker_data.json"):
            with open("time_tracker_data.json", "r") as f:
                data = json.load(f)
                
                self.tasks = [
                    Task(
                        task["name"],
                        task["project"],
                        task["tags"],
                        task["life_area"]
                    ) for task in data.get("tasks", [])
                ]
                
                for i, task in enumerate(data.get("tasks", [])):
                    self.tasks[i].total_time = timedelta(seconds=task.get("total_time", 0))
                    self.tasks[i].daily_time = {
                        k: timedelta(seconds=v) for k, v in task.get("daily_time", {}).items()
                    }
                
                self.projects = data.get("projects", [])
                self.tags = data.get("tags", [])
                self.life_areas = data.get("life_areas", [])

def main(page: ft.Page):
    TimeTrackerApp(page)

ft.app(target=main)