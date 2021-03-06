from os.path import join
from datetime import datetime

from gi.repository import Gtk, Gdk

import Config
from Task import Task



class DateDialog(Gtk.MessageDialog):

    def __init__(self, parent, task):
        Gtk.MessageDialog.__init__(self, parent,
                                   buttons=Gtk.ButtonsType.OK_CANCEL)
        self.task = task
        self.set_title(task.title)

        # Add calendar
        builder = Gtk.Builder()
        builder.add_from_file(join(Config.DESIGN_DIR, "DateEditDialog.glade"))
        box = self.get_message_area()
        for child in box.get_children():
            box.remove(child)

        content = builder.get_object("all")
        box.add(content)
        self.calendar = builder.get_object("calendar")
        self.useDate = builder.get_object("useDateCheckButton")
        self.useDate.connect("toggled", self.update_calendar_sensivity)

        if self.task.date:
            self.calendar.select_day(task.date[2])
            # Gtk Calendar numbers the months from 0 to 11
            self.calendar.select_month(task.date[1] - 1, task.date[0])
            self.useDate.set_active(True)
        else:
            now = datetime.now()
            self.calendar.select_day(now.day)
            # Gtk Calendar numbers the months from 0 to 11
            self.calendar.select_month(now.month - 1, now.year)

        self.show_all()


    def update_calendar_sensivity(self, *args):
        self.calendar.set_sensitive(self.useDate.get_active())


    def run(self):
        """Run Dialog

        Return:
            date selected, None if date removed, task date on cancel

        """
        result = Gtk.MessageDialog.run(self)
        if not self.useDate.get_active():
            return None

        if result == -5:  # OK
            date = self.calendar.get_date()
            # GTK Calendar numbers months from 0 to 11
            return (date[0], date[1] + 1, date[2])
        else:
            return self.task.date



class TaskEditDialog(Gtk.MessageDialog):

    def __init__(self, parent, task_=None):
        Gtk.MessageDialog.__init__(self, parent,
                                   buttons=Gtk.ButtonsType.OK_CANCEL)
        if task_:
            self.set_title(task_.title)
        # Add content
        box = self.get_message_area()
        for child in box.get_children():
            box.remove(child)

        builder = Gtk.Builder()
        pathToDialogXML = join(Config.DESIGN_DIR, "TitleDescEditDialog.glade")
        builder.add_from_file(pathToDialogXML)

        content = builder.get_object("newTask")
        self.titleEntry = builder.get_object("newTaskNameEntry")
        self.descriptionEntry = builder.get_object("newTaskDescriptionEntry")

        # Fill entries with information present in task
        if task_:
            self.titleEntry.set_text(task_.title)
            self.descriptionEntry.get_buffer().set_text(task_.description)

        box.add(content)
        self.show_all()


    def run(self):
        """Run Dialog

        Return:
            (newTitle, newDescription)

        """
        result = Gtk.MessageDialog.run(self)
        if result == -5:  # OK
            newTitle = self.titleEntry.get_text()
            buffer_ = self.descriptionEntry.get_buffer()
            start = buffer_.get_start_iter()
            end = buffer_.get_end_iter()
            newDescription = buffer_.get_text(start, end, True)
            return (newTitle, newDescription)
        else:
            return None



class NewTaskDialog(Gtk.MessageDialog):

    def __init__(self, parent, task_=None, color=None):
        Gtk.MessageDialog.__init__(self, parent,
                                   buttons=Gtk.ButtonsType.OK_CANCEL)
        # TODO translation
        self.set_title("New task")

        # Add content
        box = self.get_content_area()
        box.remove(box.get_children()[0])

        builder = Gtk.Builder()
        pathToDialogXML = join(Config.DESIGN_DIR, "NewTaskWidget.glade")
        builder.add_from_file(pathToDialogXML)

        newTaskWidget = builder.get_object("newTaskWidget")
        box.add(newTaskWidget)
        box.set_border_width(6)

        # Get objects
        self.nameEntry = builder.get_object("taskNameEntry")
        self.descriptionEntry = builder.get_object("taskDescriptionView")
        self.useCalendarCheck = builder.get_object("AddDateCheckButton")
        self.calendar = builder.get_object("calendar")
        self.colorButton = builder.get_object("colorButton")

        defaultColor = Gdk.RGBA()
        if color:
            defaultColor.parse(color)
            defaultColor.blue *= 0.8
            defaultColor.red *= 0.8
            defaultColor.green *= 0.8
        else:
            defaultColor.parse("#FFFFFF")
        self.colorButton.set_rgba(defaultColor)

        now = datetime.now()
        self.calendar.select_day(now.day)
        # Gtk Calendar numbers the months from 0 to 11
        self.calendar.select_month(now.month - 1, now.year)

        # Connect to signals
        signals = {"addDateToggled": self._on_add_date_toggled}
        builder.connect_signals(signals)


    def _on_add_date_toggled(self, *args):
        self.calendar.set_sensitive(self.useCalendarCheck.get_active())


    def run(self):
        """Run Dialog

        Return:
            (title, description, date, color)

        """
        result = Gtk.MessageDialog.run(self)
        if result == -5:  # OK
            title = self.nameEntry.get_text()
            buffer_ = self.descriptionEntry.get_buffer()
            start = buffer_.get_start_iter()
            end = buffer_.get_end_iter()
            description = buffer_.get_text(start, end, True)
            if self.useCalendarCheck.get_active():
                tdate = self.calendar.get_date()
                date = (tdate[0], tdate[1] + 1, tdate[2])
            else:
                date = None
            color = self.colorButton.get_rgba()
            return (title, description, date, color)
        else:
            return None



class TaskEditPopover(Gtk.Popover):

    def __init__(self, taskWidget):
        Gtk.Popover.__init__(self)
        self.set_relative_to(taskWidget._primaryContentHolder)
        self.set_position(Gtk.PositionType.RIGHT)
        self.task = taskWidget.task
        self.mainWindow = taskWidget.get_toplevel()

        self.builder = Gtk.Builder()
        self.builder.add_from_file(join(Config.DESIGN_DIR,
                                        "TaskPopover.glade"))

        handlers = {"onEditText": self._on_text_edit,
                    "onEditDate": self._on_date_edit,
                    "onRemoveDate": self._on_date_remove}
        self.builder.connect_signals(handlers)

        self.stack = Gtk.Stack()
        self.stack.set_homogeneous(False)
        self.add(self.stack)
        self._create_main_menu()
        self._create_submenus()
        self.show_all()
        self.stack.set_visible_child(self.mainMenu)
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)


    def _create_main_menu(self):
        self.mainMenu = Gtk.ListBox()
        self.mainMenu.set_selection_mode(Gtk.SelectionMode.NONE)
        self.mainMenu.modify_bg(0, Gdk.Color.parse(Config.DEFAULT_BG)[1])

        labels = ["viewDesc", "addSubtask", "editText", "editColor",
                  "editDate", "archive"]
        if self.task.archived:
            labels[5] = "dearchive"

        for labelName in labels:
            row = Gtk.ListBoxRow()
            row.add(self.builder.get_object(labelName))
            row.modify_bg(0, Gdk.Color.parse(Config.DEFAULT_BG)[1])
            row.modify_bg(2, Gdk.Color.parse(Config.SHADE)[1])
            self.mainMenu.add(row)

        self.stack.add(self.mainMenu)
        self.mainMenu.connect("row-activated", self._on_menu_item_activate)
        self.stack.show_all()


    def _create_submenus(self):
        self._create_view_description_submenu()
        self._create_text_edit_submenu()
        self._create_date_edit_submenu()
        self.stack.show_all()


    def _on_menu_item_activate(self, listbox, row):
        self.set_modal(False)
        index = row.get_index()
        if index == 0:  # Show description
            self._show_description()
        elif index == 1:  # Add subtask
            add_subtask(self.mainWindow, self.task)
            self.hide()
        elif index == 2:  # Edit texts
            self._edit_texts()
        elif index == 3:  # Edit color
            self.hide()
            edit_task_color(self.task)
        elif index == 4:  # Edit date
            self._edit_date()
        elif index == 5:  # Archive
            if self.task.archived:
                self.task.dearchive()
            else:
                self.task.archive()
            self.hide()


    def _create_view_description_submenu(self):
        self.descriptionScrolled = Gtk.ScrolledWindow()
        self.descriptionScrolled.set_policy(Gtk.PolicyType.AUTOMATIC,
                                            Gtk.PolicyType.AUTOMATIC)
        self.descriptionScrolled.set_size_request(Config.DESCRIPTION_WIDTH, -1)
        self.descriptionLabel = self.builder.get_object("description")
        wrapperBox = Gtk.Box()
        wrapperBox.pack_start(self.descriptionLabel, True, True, 0)
        self.descriptionScrolled.add(wrapperBox)
        self.descriptionScrolled.show_all()
        if self.task.description:
            self.descriptionLabel.set_text(self.task.description)
        self.stack.add(self.descriptionScrolled)


    def _create_text_edit_submenu(self):
        self.textEdit = self.builder.get_object("editTextMenu")
        self.titleEntry = self.builder.get_object("newTaskNameEntry")
        self.descriptionEntry = self.builder.get_object(
            "newTaskDescriptionEntry")
        self.titleEntry.set_text(self.task.title)
        self.descriptionEntry.get_buffer().set_text(self.task.description)
        self.stack.add(self.textEdit)


    def _create_date_edit_submenu(self):
        self.dateEdit = self.builder.get_object("editDateMenu")
        self.calendar = self.builder.get_object("calendar")
        if self.task.date:
            self.calendar.select_day(self.task.date[2])
            # Gtk Calendar numbers the months from 0 to 11
            self.calendar.select_month(
                self.task.date[1] - 1, self.task.date[0])
        else:
            now = datetime.now()
            self.calendar.select_day(now.day)
            # Gtk Calendar numbers the months from 0 to 11
            self.calendar.select_month(now.month - 1, now.year)
        self.stack.add(self.dateEdit)


    def _show_description(self):
        self.stack.set_visible_child(self.descriptionScrolled)


    def _edit_texts(self):
        self.stack.set_visible_child(self.textEdit)


    def _edit_date(self):
        self.stack.set_visible_child(self.dateEdit)


    def _on_text_edit(self, button):
        newTitle = self.titleEntry.get_text()
        buffer_ = self.descriptionEntry.get_buffer()
        start = buffer_.get_start_iter()
        end = buffer_.get_end_iter()
        newDescription = buffer_.get_text(start, end, True)
        self.task.set_title(newTitle)
        self.task.set_description(newDescription)
        self.hide()


    def _on_date_edit(self, button):
        newDate = self.calendar.get_date()
        # Gtk Calendar numbers the months from 0 to 11
        newDate = (newDate[0], newDate[1] + 1, newDate[2])
        self.task.set_date(newDate)
        self.hide()


    def _on_date_remove(self, button):
        newDate = None
        self.task.set_date(newDate)
        self.hide()



def edit_task_title_description(toplevel, task):
    """Create Dialog to edit task title and description"""
    dialog = TaskEditDialog(toplevel, task)
    newTitle, newDescription = None, None
    try:
        newTitle, newDescription = dialog.run()
    except TypeError:  # Cancel
        pass
    finally:
        dialog.destroy()
    task.set_title(newTitle)
    task.set_description(newDescription)
    return newTitle, newDescription


def edit_task_date(toplevel, task):
    """Create Dialog to edit date task is due to"""
    dialog = DateDialog(toplevel, task)
    result = dialog.run()

    task.set_date(result)
    dialog.destroy()


def edit_task_color(task):
    """Create Dialog to edit task color"""

    dialog = Gtk.ColorChooserDialog()
    color = Gdk.RGBA()
    color.parse(task.color)
    dialog.set_rgba(color)
    result = dialog.run()
    if result == -5:  # OK
        color = dialog.get_rgba()
        task.set_color(strFromColor(color))
    dialog.destroy()


def add_subtask(toplevel, task):
    """Create Dialog to edit task title and description"""
    dialog = NewTaskDialog(toplevel, color=task.color)
    try:
        newTitle, newDescription, newDate, newColor = dialog.run()
    except TypeError:  # Cancel
        return None
    finally:
        dialog.destroy()

    if not newTitle:
        return  # Empty title = Cancel
    newTask = Task(newTitle)
    if newDescription:
        newTask.description = newDescription
    if newDate:
        newTask.date = newDate
    newTask.color = strFromColor(newColor)
    task.add_subtask(newTask)
    return newTask


def strFromColor(color):
    redStr = "{0:02x}".format(int(color.red * 255))
    greenStr = "{0:02x}".format(int(color.green * 255))
    blueStr = "{0:02x}".format(int(color.blue * 255))
    return "#{r}{g}{b}".format(r=redStr, g=greenStr, b=blueStr)
