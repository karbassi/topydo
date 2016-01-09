# Topydo - A todo.txt client written in Python.
# Copyright (C) 2015 Bram Schoenmakers <me@bramschoenmakers.nl>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import urwid

from topydo.ui.TodoWidget import TodoWidget


class PendingAction(object):
    """
    Object class for storing TodoListWidget action waiting for execution.
    """
    def __init__(self, p_tlw, p_action_str, p_size):
        self.todolist = p_tlw
        self.action_str = p_action_str
        self.size = p_size

    def execute(self, p_loop, p_user_data=None):
        """
        Executes action stored in action_str attribute from within p_loop
        (typically urwid.MainLoop).

        Since this method is primarily used as callback for
        urwid.MainLoop.set_alarm_in it has to accept 3rd parameter: p_user_data.
        """
        self.todolist.resolve_action(self.action_str, self.size)
        self.todolist.keystate = None


class TodoListWidget(urwid.LineBox):
    def __init__(self, p_view, p_title, p_keymap):
        self._view = None

        self.keymap = p_keymap
        # store a state for multi-key shortcuts (e.g. 'gg')
        self.keystate = None
        # store offset length for postpone command (e.g. '3' for 'p3w')
        self._pp_offset = None

        self._title_widget = urwid.Text(p_title, align='center')

        self.todolist = urwid.SimpleFocusListWalker([])
        self.listbox = urwid.ListBox(self.todolist)
        self.view = p_view

        pile = urwid.Pile([
            (1, urwid.Filler(self._title_widget)),
            (1, urwid.Filler(urwid.Divider('\u2500'))),
            ('weight', 1, self.listbox),
        ])

        pile.focus_position = 2

        super().__init__(pile)

        urwid.register_signal(TodoListWidget, ['execute_command_silent',
                                               'execute_command',
                                               'refresh',
                                               'add_pending_action',
                                               'remove_pending_action',
                                               ])

    @property
    def view(self):
        return self._view

    @view.setter
    def view(self, p_view):
        self._view = p_view
        self.update()

    @property
    def title(self):
        return self._title_widget.text

    @title.setter
    def title(self, p_title):
        self._title_widget.set_text(p_title)

    def update(self):
        """
        Updates the todo list according to the todos in the view associated
        with this list.
        """
        old_focus_position = self.todolist.focus

        del self.todolist[:]

        for todo in self.view.todos:
            todowidget = TodoWidget(todo, self.view.todolist.number(todo))
            self.todolist.append(todowidget)
            self.todolist.append(urwid.Divider('-'))

        if old_focus_position:
            try:
                self.todolist.set_focus(old_focus_position)
            except IndexError:
                # scroll to the bottom if the last item disappeared from column
                # -2 for the same reason as in self._scroll_to_bottom()
                self.todolist.set_focus(len(self.todolist) - 2)

    def _scroll_to_top(self, p_size):
        self.listbox.set_focus(0)

        # see comment at _scroll_to_bottom
        self.listbox.calculate_visible(p_size)

    def _scroll_to_bottom(self, p_size):
        # -2 because the last Divider shouldn't be focused.
        end_pos = len(self.listbox.body) - 2
        self.listbox.set_focus(end_pos)

        # for some reason, set_focus doesn't rerender the list.
        # calculate_visible is the only public method (besides keypress) that
        # deals with pending focus changes.
        self.listbox.calculate_visible(p_size)

    def keypress(self, p_size, p_key):
        urwid.emit_signal(self, 'remove_pending_action')

        keymap, keystates = self.keymap

        shortcut = self.keystate or ''
        shortcut += p_key

        try:
            action = keymap[shortcut]
        except KeyError:
            action = None

        if action:
            if shortcut in keystates:
                # Supplied key-shortcut matches keystate and action. Save the
                # keystate in case user will hit another key and add an action
                # waiting for execution if user won't type anything further.
                self.keystate = shortcut
                self._add_pending_action(action, p_size)
            else:
                # Only action is matched. Handle it and reset keystate.
                self.resolve_action(action, p_size)
                self.keystate = None
            return
        else:
            if shortcut in keystates:
                self.keystate = shortcut
            else:
                try:
                    # Check whether current keystate matches built-in 'postpone'
                    # action.
                    mode = keymap[self.keystate]
                    if mode in ['postpone', 'postpone_s']:
                        if self._postpone_selected(p_key, mode) is not None:
                            self.keystate = None
                    return
                except KeyError:
                    if not self.keystate:
                        # Single key that is not described in keymap config.
                        return self.listbox.keypress(p_size, p_key)
                    self.keystate = None
            return

    def mouse_event(self, p_size, p_event, p_button, p_column, p_row, p_focus):
        if p_event == 'mouse press':
            if p_button == 4:  # up
                self.listbox.keypress(p_size, 'up')
                return
            elif p_button == 5:  # down:
                self.listbox.keypress(p_size, 'down')
                return

        return super().mouse_event(p_size,  # pylint: disable=E1102
                                   p_event,
                                   p_button,
                                   p_column,
                                   p_row,
                                   p_focus)

    def selectable(self):
        return True

    def _execute_on_selected(self, p_cmd_str):
        """
        Executes command specified by p_cmd_str on selected todo item.

        p_cmd_str should be a string with one replacement field ('{}') which
        will be substituted by id of the selected todo item.
        """
        try:
            todo = self.listbox.focus.todo
            todo_id = str(self.view.todolist.number(todo))

            urwid.emit_signal(self,
                              'execute_command_silent',
                              p_cmd_str.format(todo_id))

            # force screen redraw after editing
            if p_cmd_str.startswith('edit'):
                urwid.emit_signal(self, 'refresh')
        except AttributeError:
            # No todo item selected
            pass

    def resolve_action(self, p_action_str, p_size=None):
        """
        Checks whether action specified in p_action_str is "built-in" or
        contains topydo command (i.e. starts with 'cmd') and forwards it to
        proper executing methods.

        p_size should be specified for some of the builtin actions like 'up' or
        'home' as they can interact with urwid.ListBox.keypress or
        urwid.ListBox.calculate_visible.
        """
        if p_action_str.startswith('cmd '):
            # cut 'cmd' word from command string
            cmd = p_action_str[4:]
            if '{}' in cmd:
                self._execute_on_selected(cmd)
            else:
                urwid.emit_signal(self, 'execute_command', cmd)
        else:
            self.execute_builtin_action(p_action_str, p_size)

    def execute_builtin_action(self, p_action_str, p_size=None):
        """
        Executes built-in action specified in p_action_str.

        Currently supported actions are: 'up', 'down', 'home', 'end',
        'postpone', 'postpone_s' and 'pri'.
        """
        if p_action_str in ['up', 'down']:
            self.listbox.keypress(p_size, p_action_str)
        elif p_action_str == 'home':
            self._scroll_to_top(p_size)
        elif p_action_str == 'end':
            self._scroll_to_bottom(p_size)
        elif p_action_str in ['postpone', 'postpone_s']:
            pass
        elif p_action_str == 'pri':
            pass

    def _add_pending_action(self, p_action, p_size):
        """
        Creates action waiting for execution and forwards it to the mainloop.
        """
        urwid.emit_signal(self, 'add_pending_action', PendingAction(self,
                                                                    p_action,
                                                                    p_size))

    def _postpone_selected(self, p_pattern, p_mode):
        """
        Postpones selected todo item by <COUNT><PERIOD>.

        Returns True after 'postpone' command is called (i.e. p_pattern is valid
        <PERIOD>), False when p_pattern is invalid and None if p_pattern is
        digit (i.e. part of <COUNT>).

        p_pattern accepts digit (<COUNT>) or one of the <PERIOD> letters:
        'd'(ay), 'w'(eek), 'm'(onth), 'y'(ear). If digit is specified, it is
        appended to _pp_offset attribute. If p_pattern contains one of the
        <PERIOD> letters, 'postpone' command is forwarded to execution with
        value of _pp_offset attribute used as <COUNT>. If _pp_offset is None,
        <COUNT> is set to 1.

        p_mode should be one of 'postpone_s' or 'postpone'. It decides whether
        'postpone' command should be called with or without '-s' flag.
        """
        if p_pattern.isdigit():
            if not self._pp_offset:
                self._pp_offset = ''
            self._pp_offset += p_pattern
            result = None
        else:
            if p_pattern in ['d', 'w', 'm', 'y']:
                offset = self._pp_offset or '1'
                if p_mode == 'postpone':
                    pp_cmd = 'cmd postpone {} '
                else:
                    pp_cmd = 'cmd postpone -s {} '
                pp_cmd += offset + p_pattern
                self.resolve_action(pp_cmd)
                result = True
            self._pp_offset = None
            result = False
        return result
