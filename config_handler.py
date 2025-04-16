# Copyright of Amazon Web Services, Inc. (AWS) 2023
#
# This code is licensed under the AWS Intellectual Property License, which can
# be found here: https://aws.amazon.com/legal/aws-ip-license-terms/; provided
# that AWS grants you a limited, royalty-free, revocable, non-exclusive,
# non-sublicensable, non-transferrable license to modify the code for internal
# testing purposes. Your receipt of this code is subject to any non-disclosure
# (or similar) agreement between you and AWS.

import argparse
from typing import Optional, Type, TypeVar
import confuse

import sys

test_config: confuse.Configuration
"""Indexable by `str` test configuration"""

pytest_args: list[str]
"""List of args to pass to pytest"""


class ConfigSingleton(sys.__class__):  # type: ignore
    _test_config: Optional[confuse.Configuration] = None
    _pytest_args: Optional[list[str]] = None

    def _initialize_config(self):
        if self._test_config:
            return
        arg_parser = argparse.ArgumentParser(
            description=
            "The ExpressLink tests runner. See README for more information.")
        arg_parser.add_argument(
            "--config",
            type=str,
            help="Specify the path to a .yaml config for eltest",
            default="eltest_config.yaml",
            required=False,
        )
        config_path = arg_parser.parse_known_args()[0].config
        self._test_config = confuse.Configuration('eltest')
        self._test_config.set_file(config_path)
        for key in self._test_config.keys():
            # Add optional override arguments for every key
            # in the test config yaml
            key_type = type(self._test_config[key].get())
            key = "--" + key
            if key_type == list:
                arg_parser.add_argument(key, action='append', required=False)
            else:
                arg_parser.add_argument(key, type=key_type, required=False)
        config_args, self._pytest_args = arg_parser.parse_known_args()
        self._test_config.set_args(config_args)

    @property
    def test_config(self) -> confuse.Configuration:
        if not self._test_config:
            self._initialize_config()
            assert self._test_config is not None and self._pytest_args is not None
        return self._test_config

    @property
    def pytest_args(self) -> list[str]:
        if not self._pytest_args:
            self._initialize_config()
            assert self._test_config is not None and self._pytest_args is not None
        return self._pytest_args

    @pytest_args.setter
    def pytest_args(self, value) -> None:
        if not self._pytest_args:
            self._initialize_config()
            assert self._test_config is not None and self._pytest_args is not None
        self._pytest_args = value


sys.modules[__name__].__class__ = ConfigSingleton  # type: ignore

T = TypeVar('T')


def get(key: str, type: Type[T]) -> T:
    """Gets a variable from test_config and asserts if it is not type(T)

    Raises KeyError if key is not in test_config"""
    value = get_or_none(key, type)
    if value is None:
        raise KeyError(f'{key=} not found in pytest config YAML')
    return value


def get_or_none(key: str, type: Type[T]) -> Optional[T]:
    """Gets a variable from test_config and asserts if it is not type(T)

    Returns None if key is not in test_config"""
    if key not in sys.modules[__name__].test_config:
        return None
    value = sys.modules[__name__].test_config[key].get(type)
    assert isinstance(value, type)
    return value
