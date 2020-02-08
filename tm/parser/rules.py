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


class ProjectAttributes(OrRule):
    rules = [
        Now(),
    ]


class ProjectHeader(AndRule):
    rules = ['project', Id(optional=True), String(), DatetimeInterval()]


class Project(AndRule):
    rules = [
        ProjectHeader(),
        *attributes(ProjectAttributes),
    ]


# Resource


class Email(AndRule):
    rules = ['email', String()]


class ResourceAttributes(OrRule):
    rules = [
        Email(),
    ]


class ResourceHeader(AndRule):
    rules = ['resource', Id(), String()]


class Resource(AndRule):
    rules = [
        ResourceHeader(),
        *attributes(ResourceAttributes, recursive=True),
    ]


# Task


class Allocate(AndRule):
    rules = ['allocate', Id()]


class Effort(AndRule):
    rules = ['effort', Timedelta()]


class TaskAttributes(OrRule):
    rules = [
        Allocate(),
        Effort(),
    ]


class TaskHeader(AndRule):
    rules = ['task', Id(), String()]


class Task(AndRule):
    rules = [
        TaskHeader(),
        *attributes(TaskAttributes, recursive=True),
    ]


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
