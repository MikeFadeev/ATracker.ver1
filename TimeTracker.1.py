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

    def get_formatted_time(self):
        total_seconds = int(self.get_current_time().total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

class TimeTrackerApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Time Tracker"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        # self.page.window_width = 800
        # self.page.window_height = 600
        
        self.tasks = []
        self.projects = []
        self.tags = []
        self.life_areas = []
        
        self.active_task = None
        self.load_data()
        self.setup_ui()
        self.page.run_task(self.update_timer)
        self.page.run_task(self.daily_checker)

    def setup_ui(self):
        self.task_name_input = ft.TextField(label="Task Name", expand=True)
        self.project_dropdown = ft.Dropdown(label="Project", options=[], expand=True)
        self.tag_chips = ft.Row(wrap=True)
        self.life_area_dropdown = ft.Dropdown(label="Life Area", options=[], expand=True)
        
        self.task_list = ft.ListView(expand=True)
        self.stats_view = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        add_task_btn = ft.ElevatedButton("Add Task", on_click=self.add_task)
        manage_projects_btn = ft.ElevatedButton("Manage Projects", on_click=self.show_manage_projects)
        manage_tags_btn = ft.ElevatedButton("Manage Tags", on_click=self.show_manage_tags)
        manage_life_areas_btn = ft.ElevatedButton("Manage Life Areas", on_click=self.show_manage_life_areas)
        
        self.tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="Tasks", content=self.task_list),
                ft.Tab(text="Statistics", content=self.stats_view),
            ],
            expand=True,
        )
        
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

#Статистика

    def update_ui(self):
        self.update_dropdowns()
        self.update_tags()
        self.update_task_list()
        self.update_stats_view()  # Добавлен вызов обновления статистики
        self.page.update()
    
    def update_stats_view(self):
        # Собираем данные для статистики
        project_stats = self.calculate_stats("project")
        life_area_stats = self.calculate_stats("life_area")
        tag_stats = self.calculate_stats("tags")
        
        # Создаем диаграммы
        project_chart = self.create_pie_chart(project_stats, "Time by Projects")
        life_area_chart = self.create_pie_chart(life_area_stats, "Time by Life Areas")
        tag_chart = self.create_pie_chart(tag_stats, "Time by Tags")
        
        # Обновляем представление статистики
        self.stats_view.controls = [
            ft.Text("Statistics", size=24, weight=ft.FontWeight.BOLD),
            project_chart,
            life_area_chart,
            tag_chart,
        ]
    
    def calculate_stats(self, category):
        stats = {}
        for task in self.tasks:
            total_seconds = task.get_current_time().total_seconds()
            
            if category == "project":
                key = task.project or "No Project"
                if key not in stats:
                    stats[key] = 0
                stats[key] += total_seconds
            
            elif category == "life_area":
                key = task.life_area or "No Life Area"
                if key not in stats:
                    stats[key] = 0
                stats[key] += total_seconds
            
            elif category == "tags":
                if not task.tags:
                    key = "No Tags"
                    if key not in stats:
                        stats[key] = 0
                    stats[key] += total_seconds
                else:
                    for tag in task.tags:
                        if tag not in stats:
                            stats[tag] = 0
                        stats[tag] += total_seconds / len(task.tags)
        
        # Фильтруем нулевые значения и сортируем
        stats = {k: v for k, v in stats.items() if v > 0}
        return dict(sorted(stats.items(), key=lambda item: item[1], reverse=True))
    
    def create_pie_chart(self, data, title):
        if not data:
            return ft.Column([
                ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
                ft.Text("No data available", style=ft.TextStyle(italic=True)),
                ft.Divider()
            ])
        
        total = sum(data.values())
        colors = [
            ft.Colors.BLUE,
            ft.Colors.GREEN,
            ft.Colors.AMBER,
            ft.Colors.RED,
            ft.Colors.PURPLE,
            ft.Colors.CYAN,
            ft.Colors.ORANGE,
            ft.Colors.PINK,
            ft.Colors.TEAL,
            ft.Colors.INDIGO,
        ]
        
        # Создаем секции диаграммы
        sections = []
        legend_items = []
        
        for i, (label, value) in enumerate(data.items()):
            percentage = (value / total) * 100
            color = colors[i % len(colors)]
            
            sections.append(
                ft.PieChartSection(
                    value=percentage,
                    color=color,
                    title=f"{percentage:.1f}%",
                    title_style=ft.TextStyle(
                        color=ft.Colors.WHITE,
                        size=12,
                        weight=ft.FontWeight.BOLD
                    ),
                    radius=100,
                )
            )
            #time = self.format_time(value)
            legend_items.append(
                ft.Row([
                    ft.Container(
                        width=20,
                        height=20,
                        bgcolor=color,
                        border_radius=5,
                        # time = self.format_time(value)
                        margin=ft.margin.only(right=5),
                        content=ft.Text(f"{label} ({self.format_time(value)})"))
                ])
            )
        
        chart = ft.PieChart(
            sections=sections,
            sections_space=1,
            center_space_radius=30,
            height=300,
            width=300,
        )
        
        return ft.Column([
            ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
            ft.Row(
                [
                    chart,
                    ft.Column(legend_items, spacing=5)
                ],
                spacing=20,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Divider()
        ])
    
    def format_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

    
    #statiatics end

    async def update_timer(self):
        while True:
            if self.active_task:
                self.update_active_task()
            await asyncio.sleep(1)

    async def daily_checker(self):
        while True:
            self.check_new_day()
            await asyncio.sleep(60)

    def update_active_task(self):
        for control in self.task_list.controls:
            if isinstance(control, ft.Card) and control.color == ft.Colors.BLUE:
                for content in control.content.content.controls:
                    if isinstance(content, ft.Text) and content.value.startswith("Time spent:"):
                        content.value = f"Time spent: {self.active_task.get_formatted_time()}"
                        break
        self.page.update()

    def update_ui(self):
        self.update_dropdowns()
        self.update_tags()
        self.update_task_list()
        self.update_stats_view()
        self.page.update()

    def update_dropdowns(self):
        self.project_dropdown.options = [ft.dropdown.Option(text="None")]
        self.project_dropdown.options.extend([
            ft.dropdown.Option(text=p) for p in sorted(self.projects)
        ])
        
        self.life_area_dropdown.options = [ft.dropdown.Option(text="None")]
        self.life_area_dropdown.options.extend([
            ft.dropdown.Option(text=la) for la in sorted(self.life_areas)
        ])

    def update_tags(self):
        self.tag_chips.controls = []
        for tag in sorted(self.tags):
            chip = ft.Chip(
                label=ft.Text(tag),
                on_select=lambda e, t=tag: self.toggle_task_tag(t),
            )
            self.tag_chips.controls.append(chip)

    def update_task_list(self):
        self.task_list.controls = []
        for task in self.tasks:
            self.task_list.controls.append(self.create_task_card(task))

    def create_task_card(self, task):
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.TIMER if task.is_active else ft.Icons.TIMER_OUTLINED),
                        title=ft.Text(task.name),
                        subtitle=ft.Text(
                            f"Project: {task.project or 'None'}\n"
                            f"Tags: {', '.join(task.tags) or 'None'}\n"
                            f"Life Area: {task.life_area or 'None'}"
                        ),
                    ),
                    ft.Text(f"Time spent: {task.get_formatted_time()}"),
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.EDIT, on_click=lambda e, t=task: self.edit_task(t)),
                        ft.IconButton(icon=ft.Icons.DELETE, on_click=lambda e, t=task: self.delete_task(t)),
                    ]),
                ]),
                padding=10,
                on_click=lambda e, t=task: self.toggle_task(t),
            ),
            elevation=5,
            color=ft.Colors.BLUE if task.is_active else None,
        )

    def toggle_task(self, task):
        if self.active_task and self.active_task != task and self.active_task.is_active:
            self.active_task.toggle_active()
        
        task.toggle_active()
        self.active_task = task if task.is_active else None
        self.save_data()
        self.update_ui()

    def add_task(self, e):
        name = self.task_name_input.value.strip()
        if not name:
            return
        
        project = self.project_dropdown.value if self.project_dropdown.value != "None" else None
        life_area = self.life_area_dropdown.value if self.life_area_dropdown.value != "None" else None
        
        selected_tags = [t for t in self.tags if t in [chip.label.value for chip in self.tag_chips.controls if chip.selected]]
        
        task = Task(name, project, selected_tags, life_area)
        self.tasks.append(task)
        self.task_name_input.value = ""
        self.save_data()
        self.update_ui()

    def edit_task(self, task):
        def save_edit(e):
            task.name = name_input.value.strip()
            task.project = project_dropdown.value if project_dropdown.value != "None" else None
            task.life_area = life_area_dropdown.value if life_area_dropdown.value != "None" else None
            task.tags = [t for t in self.tags if t in [chip.label.value for chip in tag_chips.controls if chip.selected]]
            
            self.save_data()
            self.update_ui()
            self.close_dialog(dialog)

        name_input = ft.TextField(label="Task Name", value=task.name)
        
        project_dropdown = ft.Dropdown(
            label="Project",
            options=[ft.dropdown.Option(text="None")] + [ft.dropdown.Option(text=p) for p in self.projects],
            value=task.project or "None"
        )
        
        life_area_dropdown = ft.Dropdown(
            label="Life Area",
            options=[ft.dropdown.Option(text="None")] + [ft.dropdown.Option(text=la) for la in self.life_areas],
            value=task.life_area or "None"
        )
        
        tag_chips = ft.Row(wrap=True)
        for tag in self.tags:
            tag_chips.controls.append(
                ft.Chip(
                    label=ft.Text(tag),
                    selected=tag in task.tags,
                    on_select=lambda e, t=tag: None
                )
            )
        
        dialog = ft.AlertDialog(
            title=ft.Text("Edit Task"),
            content=ft.Column([
                name_input,
                project_dropdown,
                life_area_dropdown,
                ft.Text("Tags:"),
                tag_chips,
            ]),
            actions=[
                ft.TextButton("Save", on_click=save_edit),
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(dialog)),
            ]
        )
        self.page.open(dialog)
        self.page.update()

    def delete_task(self, task):
        def confirm_delete(e):
            self.tasks.remove(task)
            if self.active_task == task:
                self.active_task = None
            self.save_data()
            self.update_ui()
            self.close_dialog(dialog)

        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete task '{task.name}'?"),
            actions=[
                ft.TextButton("Yes", on_click=confirm_delete),
                ft.TextButton("No", on_click= lambda e: self.page.close(dialog)),
                # ft.TextButton("No", on_click=self.close_dialog),
            ]
        )
        self.open_dialog(dialog)

    def show_manage_projects(self, e):
        def add_project(e):
            new_project = new_project_input.value.strip()
            if new_project and new_project not in projects:
                projects.append(new_project)
                refresh_list()
                new_project_input.value = ""
                self.page.update()

        def delete_project(project):
            if project in projects:
                projects.remove(project)
                for task in self.tasks:
                    if task.project == project:
                        task.project = None
                refresh_list()
                self.page.update()

        def edit_project(project):
            def save_edit(e):
                new_name = edit_input.value.strip()
                if new_name and new_name != project and new_name not in projects:
                    index = projects.index(project)
                    projects[index] = new_name
                    for task in self.tasks:
                        if task.project == project:
                            task.project = new_name
                    self.save_data()
                    refresh_list()
                    self.close_dialog(dialog)

            edit_input = ft.TextField(value=project)
            
            dialog = ft.AlertDialog(
                title=ft.Text("Edit Project"),
                content=edit_input,
                actions=[
                    ft.TextButton("Save", on_click=save_edit),
                    ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ]
            )
            self.open_dialog(dialog)

        def refresh_list():
            projects_list.controls = [
                ft.ListTile(
                    title=ft.Text(''),
                    trailing=ft.Row([
                        ft.Text(p, size=20),
                        #ft.IconButton(icon=ft.Icons.EDIT, on_click=lambda e, p=p: edit_project(p)),
                        ft.IconButton(icon=ft.Icons.DELETE, on_click=lambda e, p=p: delete_project(p)),
                    ])
                )
                for p in sorted(projects)
            ]

        projects = self.projects.copy()
        
        new_project_input = ft.TextField(label="New Project", expand=True)
        add_btn = ft.ElevatedButton("Add", on_click=add_project)
        
        projects_list = ft.ListView(expand=True)
        refresh_list()
        
        def save_projects(e):
            self.projects = projects
            self.save_data()
            self.update_ui()
            self.close_dialog(dialog)

        dialog = ft.AlertDialog(
            title=ft.Text("Manage Projects                                                              "),
            content=ft.Column([
                ft.Text("Existing Projects:"),
                projects_list,
                ft.Divider(),
                ft.Text("Add New Project:"),
                ft.Row([new_project_input, add_btn]),
            ]),
            actions=[
                ft.TextButton("Save", on_click=save_projects),
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
            ],
            #content_padding=ft.padding.all(10)
        )
        self.open_dialog(dialog)

    def show_manage_tags(self, e):
        def add_tag(e):
            new_tag = new_tag_input.value.strip()
            if new_tag and new_tag not in tags:
                tags.append(new_tag)
                refresh_list()
                new_tag_input.value = ""
                self.page.update()

        def delete_tag(tag):
            if tag in tags:
                tags.remove(tag)
                for task in self.tasks:
                    if tag in task.tags:
                        task.tags.remove(tag)
                refresh_list()
                self.page.update()

        def edit_tag(tag):
            def save_edit(e):
                new_name = edit_input.value.strip()
                if new_name and new_name != tag and new_name not in tags:
                    index = tags.index(tag)
                    tags[index] = new_name
                    for task in self.tasks:
                        if tag in task.tags:
                            task.tags[task.tags.index(tag)] = new_name
                    refresh_list()
                    self.close_dialog(dialog)

            edit_input = ft.TextField(value=tag)
            
            dialog = ft.AlertDialog(
                title=ft.Text("Edit Tag"),
                content=edit_input,
                actions=[
                    ft.TextButton("Save", on_click=save_edit),
                    ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ]
            )
            self.open_dialog(dialog)

        def refresh_list():
            tags_list.controls = [
                ft.ListTile(
                    #title=ft.Text(t),
                    trailing=ft.Row([
                        ft.Text(t, size=20),
                        #ft.IconButton(icon=ft.Icons.EDIT, on_click=lambda e, t=t: edit_tag(t)),
                        ft.IconButton(icon=ft.Icons.DELETE, on_click=lambda e, t=t: delete_tag(t)),
                    ]),
                )
                for t in sorted(tags)
            ]

        tags = self.tags.copy()
        
        new_tag_input = ft.TextField(label="New Tag", expand=True)
        add_btn = ft.ElevatedButton("Add", on_click=add_tag)
        
        tags_list = ft.ListView(expand=True)
        refresh_list()
        
        def save_tags(e):
            self.tags = tags
            self.save_data()
            self.update_ui()
            self.close_dialog(dialog)

        dialog = ft.AlertDialog(
            title=ft.Text("Manage Tags                                                              "),
            content=ft.Column([
                ft.Text("Existing Tags:"),
                tags_list,
                ft.Divider(),
                ft.Text("Add New Tag:"),
                ft.Row([new_tag_input, add_btn]),
            ]),
            actions=[
                ft.TextButton("Save", on_click=save_tags),
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
            ],
        )
        self.open_dialog(dialog)

    def show_manage_life_areas(self, e):
        def add_life_area(e):
            new_la = new_la_input.value.strip()
            if new_la and new_la not in life_areas:
                life_areas.append(new_la)
                refresh_list()
                new_la_input.value = ""
                self.page.update()

        def delete_life_area(la):
            if la in life_areas:
                life_areas.remove(la)
                for task in self.tasks:
                    if task.life_area == la:
                        task.life_area = None
                refresh_list()
                self.page.update()

        def edit_life_area(la):
            def save_edit(e):
                new_name = edit_input.value.strip()
                if new_name and new_name != la and new_name not in life_areas:
                    index = life_areas.index(la)
                    life_areas[index] = new_name
                    for task in self.tasks:
                        if task.life_area == la:
                            task.life_area = new_name
                    refresh_list()
                    self.close_dialog(dialog)

            edit_input = ft.TextField(value=la)
            
            dialog = ft.AlertDialog(
                title=ft.Text("Edit Life Area"),
                content=edit_input,
                actions=[
                    ft.TextButton("Save", on_click=save_edit(e)),
                    ft.TextButton("Cancel", on_click=lambda e:self.close_dialog(dialog)),
                ]
            )
            self.open_dialog(dialog)

        def refresh_list():
            la_list.controls = [
                ft.ListTile(
                    #title=ft.Text(la),
                    trailing=ft.Row([
                        ft.Text(la, size=20),
                        #ft.IconButton(icon=ft.Icons.EDIT, on_click=lambda e, la=la: edit_life_area(la)),
                        ft.IconButton(icon=ft.Icons.DELETE, on_click=lambda e, la=la: delete_life_area(la)),
                    ]),
                    #content_padding=ft.padding.symmetric(horizontal=16)
                )
                for la in sorted(life_areas)
            ]

        life_areas = self.life_areas.copy()
        
        new_la_input = ft.TextField(label="New Life Area", expand=True)
        add_btn = ft.ElevatedButton("Add", on_click=add_life_area)
        
        la_list = ft.ListView(expand=True)
        refresh_list()
        
        def save_life_areas(e):
            self.life_areas = life_areas
            self.save_data()
            self.update_ui()
            self.close_dialog(dialog)

        dialog = ft.AlertDialog(
            title=ft.Text("Manage Life Areas                                                              "),
            content=ft.Column([
                ft.Text("Existing Life Areas:"),
                la_list,
                ft.Divider(),
                ft.Text("Add New Life Area:"),
                ft.Row([new_la_input, add_btn]),
            ]),
            inset_padding= ft.padding.symmetric(vertical=10, horizontal=10),
            content_padding= ft.padding.all(20),
            actions=[
                ft.TextButton("Save", on_click=save_life_areas),
                ft.TextButton("Cancel", on_click= lambda e: self.close_dialog(dialog)),
            ],
        )
        self.open_dialog(dialog)

    def open_dialog(self, dialog):
        self.page.open(dialog)
        self.page.update()

    def close_dialog(self, dialog):
        self.page.close(dialog)
        self.page.update()

    def check_new_day(self):
        today = datetime.now().date().isoformat()
        for task in self.tasks:
            if task.daily_time and today not in task.daily_time:
                if task.is_active:
                    elapsed = datetime.now() - task.start_time
                    task.total_time += elapsed
                    task.record_daily_time(elapsed)
                    task.start_time = datetime.now()
                task.daily_time[today] = timedelta()

    def save_data(self):
        data = {
            "tasks": [
                {
                    "name": task.name,
                    "project": task.project,
                    "tags": task.tags,
                    "life_area": task.life_area,
                    "is_active": task.is_active,
                    "start_time": task.start_time.isoformat() if task.start_time else None,
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
                
                self.tasks = []
                for task_data in data.get("tasks", []):
                    task = Task(
                        task_data["name"],
                        task_data["project"],
                        task_data["tags"],
                        task_data["life_area"]
                    )
                    task.is_active = task_data.get("is_active", False)
                    start_time_str = task_data.get("start_time")
                    task.start_time = datetime.fromisoformat(start_time_str) if start_time_str else None
                    task.total_time = timedelta(seconds=task_data.get("total_time", 0))
                    task.daily_time = {
                        k: timedelta(seconds=v) for k, v in task_data.get("daily_time", {}).items()
                    }
                    self.tasks.append(task)
                    
                    if task.is_active:
                        self.active_task = task
                
                self.projects = data.get("projects", [])
                self.tags = data.get("tags", [])
                self.life_areas = data.get("life_areas", [])

def main(page: ft.Page):
    TimeTrackerApp(page)

ft.app(target=main)