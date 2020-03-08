"""Perform actions in the future."""

import time
import sched
import typing
import cherrypy


class ScheduledEvent():
    """A wrapper for the named tuple returned by the scheduler.

    """

    event: sched.Event

    def __init__(self, event: sched.Event) -> None:
        self.event = event

    @property
    def cache_key(self) -> str:
        """Map an event to a string for use with the cache plugin.
        """

        return f"scheduler:{round(self.event.time, 3)}"

    @property
    def time_remaining(self) -> float:
        """How much time is left until the event is due.

        A float representing a number of fractional seconds."""

        return self.event.time - time.time()

    def persist(self) -> None:
        """Add the event to the cache."""

        values = {
            "time": self.event.time,
            "priority": self.event.priority,
            "argument": self.event.argument,
            "kwargs": self.event.kwargs
        }

        cherrypy.engine.publish(
            "cache:set",
            self.cache_key,
            values,
            self.time_remaining
        )

    def forget(self) -> None:
        """Discard the cached record of a persisted event."""

        cherrypy.engine.publish(
            "cache:clear",
            self.cache_key
        )


class Plugin(cherrypy.process.plugins.Monitor):
    """A CherryPy plugin for deferring work until a later time.

    Unlike other plugins, this is a subclass of Monitor rather than
    SimplePlugin. Monitor provides a way of doing something repeatedly
    using its internal BackgroundTask instance.

    """

    scheduler: sched.scheduler

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.Monitor.__init__(
            self,
            bus,
            self.run_scheduled_tasks,
            1,
            'MedleyScheduler'
        )

    def start(self) -> None:
        """Define the CherryPy messages to listen for and start running the
        scheduler.

        This plugin owns the scheduler prefix.

        """
        self.bus.subscribe("server:ready", self.revive)
        self.bus.subscribe("scheduler:add", self.add)
        self.bus.subscribe("scheduler:persist", self.persist)
        self.bus.subscribe("scheduler:remove", self.remove)
        self.bus.subscribe("scheduler:upcoming", self.upcoming)
        self.scheduler = sched.scheduler(time.time, time.sleep)
        cherrypy.process.plugins.Monitor.start(self)

    def run_scheduled_tasks(self) -> None:
        """Process the scheduler queue.

        The scheduler determines when the task should be
        executed, and the add() method determines what should happen.
        This is the final step where execution occurs.

        """
        self.scheduler.run(False)

    def revive(self) -> None:
        """Add back any previously-scheduled jobs that are still valid.

        This is usually only called at server start.
        """

        cached_events = cherrypy.engine.publish(
            "cache:match",
            "scheduler"
        ).pop()

        if not cached_events:
            return

        unit = "event" if len(cached_events) == 1 else "events"

        cherrypy.engine.publish(
            "applog:add",
            "scheduler",
            f"{len(cached_events)} {unit} revived"
        )

        for cached_event in cached_events:
            self.add(
                cached_event["time"] - time.time(),
                *cached_event["argument"],
                **cached_event["kwargs"]
            )

    @staticmethod
    def execute(
            name: str,
            *args: typing.Any,
            **kwargs: typing.Any
    ) -> None:
        """Run a previously-scheduled job."""
        cherrypy.engine.publish(name, *args, **kwargs)

    def add(
            self,
            delay_seconds: int,
            *args: typing.Any,
            **kwargs: typing.Any
    ) -> ScheduledEvent:
        """Schedule an event for future execution

        args should be a plugin command and arguments it expects. When
        the job is ready to execute, it will be as if
        cherrypy.engine.publish had been called directly.

        The scheduling that happens here is ephemeral. If the server
        goes down or is restarted, all scheduled events are lost. In
        cases where this is undesirable, use the persist() method
        instead.

        """

        event_tuple = self.scheduler.enter(
            delay_seconds,
            1,
            self.execute,
            args,
            kwargs
        )

        return ScheduledEvent(event_tuple)

    def persist(
            self,
            delay_seconds: int,
            *args: typing.Any,
            **kwargs: typing.Any
    ) -> ScheduledEvent:
        """Schedule an event and then cache it.

        Cache storage makes it possible for events to last across
        server restarts. By default the scheduler is normally
        ephemeral.

        For situations where persistence isn't desirable, use the
        add() method instead.

        """

        event = self.add(
            delay_seconds,
            *args,
            **kwargs
        )

        event.persist()

        return event

    def remove(self, event: typing.Union[str, sched.Event]) -> bool:
        """Cancel a previously-scheduled event.

        Event can either be a string or an object.
        """

        if isinstance(event, str):
            for event_object in self.upcoming(event):
                self.remove(event_object)
            return True

        try:
            self.scheduler.cancel(event)

            scheduled_event = ScheduledEvent(event)

            scheduled_event.forget()

            return True
        except ValueError:
            return False

    def upcoming(
            self,
            event_filter: str = None
    ) -> typing.List[sched.Event]:
        """List upcoming events in the order they will be run."""

        return [
            event for event in self.scheduler.queue
            if event.argument[0] == event_filter
            or event_filter is None
        ]
