

class Attribute:
    pass


class Tree:

    def __init__(self):
        self.nodes = []


class Node:

    def __init__(self, key, title, parent=None, tree=None):
        self.tree = tree if parent is None else parent.tree
        self.tree.nodes.append(self)

        self.parent = parent
        self.parent.children.append(self)
        self.children = []

        self.key = key
        self.title = title


class Task(Node):
    pass


class Resource(Node):
    pass


class Project:

    def __init__(self, key, title, start_date, end_date):
        self.key = key or 'project'
        self.title = title
        self.start_date = start_date
        self.end_date = end_date

        self.tasks = Tree()
        self.resources = Tree()
