from datetime import datetime

from ..lexer import tokens

from .base_rules import (
    AndRule,
    OrRule,
    E,
    Self,
)


# Variable types


class Id(AndRule):
    rules = [tokens.Name]

    @staticmethod
    def process(x, value):
        return value


class String(AndRule):
    rules = [tokens.String]

    @staticmethod
    def process(x, value):
        return value


class Timedelta(AndRule):
    rules = [tokens.Timedelta]

    @staticmethod
    def process(x, value):
        return value


class Datetime(OrRule):
    rules = [
        tokens.Datetime,
        ['%{', tokens.Datetime, '+', Timedelta(), '}'],
    ]

    @staticmethod
    def process(x, value):
        if isinstance(value, datetime):
            return value
        _, d, _, td, _ = value
        return d + td


class DatetimeInterval(AndRule):
    rules = [
        tokens.Datetime,
        [
            ['-', Datetime()],
            ['+', Timedelta()],
        ]
    ]

    @staticmethod
    def process(x, start_date, args):
        op, arg = args
        end_date = arg if op == '-' else start_date + arg
        return (start_date, end_date)


# Attributes helper


def attributes(rule_class, recursive=False):
    s = [Self] if recursive else []
    return ['{', rule_class(optional=True, repeatable=True), *s, '}']


# Project


class Now(AndRule):
    rules = ['now', Datetime()]

    @staticmethod
    def process(x, name, value):
        return {name: value}


class ProjectAttributes(OrRule):
    rules = [
        Now(),
    ]


class ProjectHeader(AndRule):
    rules = ['project', Id(optional=True), String(), DatetimeInterval()]

    @staticmethod
    def process(x, typ, *args):
        if len(args) == 2:
            args = [None] + list(args)
        oid, title, interval = args
        return {'type': typ, 'id': oid, 'start_date': interval[0], 'end_date': interval[1]}


class Project(AndRule):
    rules = [
        ProjectHeader(),
        *attributes(ProjectAttributes),
    ]

    @staticmethod
    def process(x, data, *args):
        _, *attributes, _ = args
        data['attributes'] = attributes
        return data


# Resource


class Email(AndRule):
    rules = ['email', String()]

    @staticmethod
    def process(x, name, value):
        return {name: value}


class ResourceAttributes(OrRule):
    rules = [
        Email(),
    ]


class ResourceHeader(AndRule):
    rules = ['resource', Id(), String()]

    @staticmethod
    def process(x, typ, oid, title):
        return {'type': typ, 'id': oid, 'title': title}


def _split(l, cond):
    t, f = [], []
    for i in l:
        t.append(i) if cond(i) else f.append(i)
    return t, f


class Resource(AndRule):
    rules = [
        ResourceHeader(),
        *attributes(ResourceAttributes, recursive=True),
    ]

    @staticmethod
    def process(x, data, *args):
        _, *values, _ = args
        children, attributes = _split(values, lambda x: x.get('type', None) == data['type'])
        data['attributes'] = attributes
        data['children'] = children
        return data


# Task


class Allocate(AndRule):
    rules = ['allocate', Id()]

    @staticmethod
    def process(x, name, value):
        return {name: value}


class Effort(AndRule):
    rules = ['effort', Timedelta()]

    @staticmethod
    def process(x, name, value):
        return {name: value}


class TaskAttributes(OrRule):
    rules = [
        Allocate(),
        Effort(),
    ]


class TaskHeader(AndRule):
    rules = ['task', Id(), String()]

    @staticmethod
    def process(x, typ, oid, title):
        return {'type': typ, 'id': oid, 'title': title}


class Task(AndRule):
    rules = [
        TaskHeader(),
        *attributes(TaskAttributes, recursive=True),
    ]

    @staticmethod
    def process(x, data, *args):
        _, *values, _ = args
        children, attributes = _split(values, lambda x: x.get('type') == data['type'])
        data['attributes'] = attributes
        data['children'] = children
        return data


# Start


class Properties(OrRule):
    rules = [
        Task(),
        Resource(),
    ]


class Main(AndRule):
    rules = [
        Project(),
        Properties(optional=True, repeatable=True),
        E(),
    ]

    @staticmethod
    def process(x, project, *props):
        return {'project': project, 'properties': list(props[:-1])}
