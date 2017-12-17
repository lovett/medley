import cherrypy
import sched
import time
import datetime

class Plugin(cherrypy.process.plugins.SimplePlugin):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("scheduler:add", self.add)
        self.bus.subscribe("scheduler:remove", self.remove)
        self.bus.subscribe("scheduler:upcoming", self.upcoming)
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def main(self):
        self.scheduler.run(False)

    def stop(self):
        pass

    def execute(self, name, *args, **kwargs):
        cherrypy.engine.publish(name, *args, **kwargs)

    def add(self, delay_seconds, *args, **kwargs):
        """Schedule an event for future execution

        args should be a plugin command and arguments it expects. When
        the job is ready to execute, it will be as if
        cherrpy.engine.publish had been called directly"""

        return self.scheduler.enter(delay_seconds, 1, self.execute, args, kwargs)

    def remove(self, event):
        """Cancel a previously-scheduled event

        Event should be an object, either the one returned when the
        event was added or the equivalent from the list of upcoming
        events.
        """

        try:
            self.scheduler.cancel(event)
            return True
        except ValueError:
            return False

    def upcoming(self):
        """List upcoming events in the order they will be run.

        Events are returned as named tuples with the fields:
        time, priority, action, argument, kwargs
        """
        return self.scheduler.queue or []
