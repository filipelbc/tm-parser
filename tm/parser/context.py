from ..core import (
    Project,
    Resource,
    Task,
)


PROP_CLASSES = {
    k.__name__.lower(): k
    for k in [Resource, Task]
}


class Context:

    def __init__(self):
        self.project = None
        self.prop_stack = []

    def init_project(self, *args):
        self.project = Project(*args)

    @property
    def current_prop(self):
        return self.prop_stack[-1]

    def add_prop(self, k, *args):
        self.prop_stack.append(PROP_CLASSES[k](*args))

    def set_prop_attr(self, name, value):
        pass
