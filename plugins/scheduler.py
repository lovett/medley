"""Perform actions in the future."""

import time
import sched
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for deferring work until a later time."""

    scheduler = None

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the scheduler prefix.
        """

        self.bus.subscribe("scheduler:add", self.add)
        self.bus.subscribe("scheduler:remove", self.remove)
        self.bus.subscribe("scheduler:upcoming", self.upcoming)
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def main(self):
        """Start the scheduler."""
        self.scheduler.run(False)

    @staticmethod
    def execute(name, *args, **kwargs):
        """Run a previously-scheduled job."""
        cherrypy.engine.publish(name, *args, **kwargs)

    def add(self, delay_seconds, *args, **kwargs):
        """Schedule an event for future execution

        args should be a plugin command and arguments it expects. When
        the job is ready to execute, it will be as if
        cherrypy.engine.publish had been called directly

        """

        return self.scheduler.enter(
            delay_seconds,
            1,
            self.execute,
            args,
            kwargs
        )

    def remove(self, event):
        """Cancel a previously-scheduled event.

        Event can either be a string name or an object.
        """

        if isinstance(event, str):
            for event_object in self.upcoming(event):
                self.remove(event_object)
            return

        try:
            self.scheduler.cancel(event)
            return True
        except ValueError:
            return False

    def upcoming(self, event_filter=None):
        """List upcoming events in the order they will be run.

        Events are returned as named tuples with the fields:
        time, priority, action, argument, kwargs.

        """

        events = self.scheduler.queue or []

        if event_filter:
            events = [
                event for event in events
                if event.argument[0] == event_filter
            ]

        return events
