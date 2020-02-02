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


class String(AndRule):
    rules = [tokens.String]


class Datetime(AndRule):
    rules = [tokens.Datetime]


class Timedelta(AndRule):
    rules = [tokens.Timedelta]


class DatetimeInterval(AndRule):
    rules = [
        tokens.Datetime,
        [
            ['-', Datetime()],
            ['+', Timedelta()],
        ]
    ]


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
