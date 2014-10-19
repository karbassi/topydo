# Topydo - A todo.txt client written in Python.
# Copyright (C) 2014 Bram Schoenmakers <me@bramschoenmakers.nl>
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

from datetime import date, timedelta

import CommandTest
import DoCommand
import TodoList

def _yes_prompt(self):
    return "y"

def _no_prompt(self):
    return "n"

class DoCommandTest(CommandTest.CommandTest):
    def setUp(self):
        todos = [
            "Foo id:1",
            "Bar p:1",
            "Baz p:1",
            "Recurring! rec:1d",
            "x 2014-10-18 Already complete",
        ]

        self.todolist = TodoList.TodoList(todos)
        self.today = date.today().isoformat()

    def test_do1(self):
        command = DoCommand.DoCommand(["3"], self.todolist, self.out, self.error, _no_prompt)
        command.execute()

        self.assertTrue(self.todolist.is_dirty())
        self.assertTrue(self.todolist.todo(3).is_completed())
        self.assertEquals(self.output, "x %s Baz p:1\n" % self.today)
        self.assertEquals(self.errors, "")

    def test_do_children1(self):
        command = DoCommand.DoCommand(["1"], self.todolist, self.out, self.error, _yes_prompt)
        command.execute()

        result = "  2 Bar p:1\n  3 Baz p:1\nx %s Bar p:1\nx %s Baz p:1\nx %s Foo id:1\n" % (self.today, self.today, self.today)

        for number in [1, 2, 3]:
            self.assertTrue(self.todolist.todo(number).is_completed())

        self.assertTrue(self.todolist.is_dirty())
        self.assertFalse(self.todolist.todo(4).is_completed())
        self.assertEquals(self.output, result)
        self.assertEquals(self.errors, "")

    def test_do_children2(self):
        command = DoCommand.DoCommand(["1"], self.todolist, self.out, self.error, _no_prompt)
        command.execute()

        result = "  2 Bar p:1\n  3 Baz p:1\nx %s Foo id:1\n" % self.today

        self.assertTrue(self.todolist.is_dirty())
        self.assertTrue(self.todolist.todo(1).is_completed())
        self.assertFalse(self.todolist.todo(2).is_completed())
        self.assertFalse(self.todolist.todo(3).is_completed())
        self.assertEquals(self.output, result)
        self.assertEquals(self.errors, "")

    def test_recurrence(self):
        today = date.today()
        tomorrow = today + timedelta(1)

        command = DoCommand.DoCommand(["4"], self.todolist, self.out, self.error)

        self.assertFalse(self.todolist.todo(4).has_tag('due'))

        command.execute()

        todo = self.todolist.todo(6)
        result = "  6 %s Recurring! rec:1d due:%s\nx %s Recurring! rec:1d\n" % (today.isoformat(), tomorrow.isoformat(), today.isoformat())

        self.assertTrue(self.todolist.is_dirty())
        self.assertEquals(self.output, result)
        self.assertEquals(self.errors, "")
        self.assertEquals(self.todolist.count(), 6)
        self.assertTrue(self.todolist.todo(4).is_completed())
        self.assertFalse(todo.is_completed())
        self.assertTrue(todo.has_tag('due'))

    def test_invalid1(self):
        command = DoCommand.DoCommand(["99"], self.todolist, self.out, self.error)
        command.execute()

        self.assertFalse(self.todolist.is_dirty())
        self.assertFalse(self.output)
        self.assertEquals(self.errors, "Invalid todo number given.\n")

    def test_invalid2(self):
        command = DoCommand.DoCommand(["A"], self.todolist, self.out, self.error)
        command.execute()

        self.assertFalse(self.todolist.is_dirty())
        self.assertFalse(self.output)
        self.assertEquals(self.errors, command.usage() + "\n")

    def test_already_complete(self):
        command = DoCommand.DoCommand(["5"], self.todolist, self.out, self.error)
        command.execute()

        self.assertFalse(self.todolist.is_dirty())
        self.assertEquals(self.todolist.todo(5).completion_date(), date(2014, 10, 18))
        self.assertFalse(self.output)
        self.assertEquals(self.errors, "Todo has already been completed.\n")

    def test_empty(self):
        command = DoCommand.DoCommand([], self.todolist, self.out, self.error)
        command.execute()

        self.assertFalse(self.todolist.is_dirty())
        self.assertFalse(self.output)
        self.assertEquals(self.errors, command.usage() + "\n")