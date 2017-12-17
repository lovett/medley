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

    def add(self, minutes, *args, **kwargs):
        return self.scheduler.enter(minutes * 60, 1, self.execute, args, kwargs)

    def remove(self, event):
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
