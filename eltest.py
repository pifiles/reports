#!/usr/bin/env python3

# Copyright of Amazon Web Services, Inc. (AWS) 2023
#
# This code is licensed under the AWS Intellectual Property License, which can
# be found here: https://aws.amazon.com/legal/aws-ip-license-terms/; provided
# that AWS grants you a limited, royalty-free, revocable, non-exclusive,
# non-sublicensable, non-transferrable license to modify the code for internal
# testing purposes. Your receipt of this code is subject to any non-disclosure
# (or similar) agreement between you and AWS.

import json
from typing import Optional
import pytest
import sys
from time import sleep
from polling import poll, TimeoutException
import atexit
import config_handler as cf
from pprint import pprint
import boto3
from mypy_boto3_iot import IoTClient
from mypy_boto3_iot.type_defs import CreateKeysAndCertificateResponseTypeDef
import os
from tests.commands import cmd, comms
from datetime import datetime

iot: Optional[IoTClient] = None

credentials: Optional[CreateKeysAndCertificateResponseTypeDef] = None


class DeviceLib:

    def __enter__(self):
        """Any actions needed to communicate with the device"""
        comms.initialize_device()
        return self

    def __exit__(self, type, value, traceback) -> None:
        """Actions needed to be taken whenever the program exits"""
        print("Cleaning up")
        comms.cleanup()
        print("Success")

    def reset_device(self) -> None:
        """Resets the device and confirms that it is awake"""
        print("Reseting device")
        comms.set_wake_pin()
        comms.clear_reset_pin()
        sleep(1)
        try:
            poll(lambda: not comms.get_event_pin(), step=0.1, timeout=10)
        except TimeoutException:
            pass
        comms.set_reset_pin()
        poll(comms.get_event_pin, step=0.1, timeout=120)
        cmd("AT+FACTORY_RESET\r\n", False)
        try:
            poll(lambda: not comms.get_event_pin(), step=0.1, timeout=10)
        except TimeoutException:
            pass
        poll(comms.get_event_pin, step=0.1, timeout=120)
        print("Done")
        comms.flush_comms()
        assert cmd("AT+EVENT?\n", False) == "OK 2 0 STARTUP\r\n"

    def get_device_info(self) -> dict[str, str]:
        """Retrieves device information and returns in a dict"""
        version_resp = cmd("AT+CONF? Version\r\n", False)
        assert "OK " in version_resp
        techspec_resp = cmd("AT+CONF? TechSpec\r\n", False)
        assert "OK " in techspec_resp
        thing_name_resp = cmd("AT+CONF? ThingName\r\n", False)
        assert "OK " in thing_name_resp
        about_resp = cmd("AT+CONF? About\r\n", False)
        assert "OK " in about_resp
        certificate_resp = cmd("AT+CONF? Certificate\r\n", False)
        assert "OK " in certificate_resp
        staging_endpoint_resp = cmd("AT+CONF? Endpoint\r\n", False)
        assert "OK " in staging_endpoint_resp
        device_info = {
            'device_version': version_resp[3:-2],
            'device_techspec': techspec_resp[3:-2],
            'thing_name': thing_name_resp[3:-2],
            'about': about_resp[3:-2],
            'certificate': certificate_resp[3:-2],
            'staging_endpoint': staging_endpoint_resp[3:-2]
        }
        return device_info


def generate_test_credentials() -> None:
    credentials_dir = os.path.relpath("credentials")
    if not os.path.exists(credentials_dir):
        os.makedirs(credentials_dir)

    assert iot is not None
    credentials = iot.create_keys_and_certificate(setAsActive=True)

    policy_document = json.dumps({
        "Version":
        "2012-10-17",
        "Statement": [{
            "Effect":
            "Allow",
            "Action": [
                "iot:Connect", "iot:Publish", "iot:Subscribe", "iot:Receive",
                "iot:DeleteThingShadow", "iot:GetThingShadow",
                "iot:UpdateThingShadow"
            ],
            "Resource":
            "*"
        }]
    })

    try:
        iot.create_policy(policyName="ExpressLink_Tests_Policy",
                          policyDocument=policy_document)
    except iot.exceptions.ResourceAlreadyExistsException:
        # Policy already exists, just continue
        pass
    iot.attach_policy(policyName="ExpressLink_Tests_Policy",
                      target=credentials["certificateArn"])

    cert_path = os.path.join(credentials_dir, "tests-certificate.crt")
    with open(cert_path, "wt") as cert_file:
        cert_file.write(credentials["certificatePem"])

    key_path = os.path.join(credentials_dir, "tests-private.key")
    with open(key_path, "wt") as key_file:
        key_file.write(credentials["keyPair"]["PrivateKey"])

    def cleanup_credentials():
        iot.detach_policy(policyName="ExpressLink_Policy_Permissive",
                          target=credentials["certificateArn"])
        iot.update_certificate(certificateId=credentials["certificateId"],
                               newStatus='INACTIVE')
        iot.delete_certificate(certificateId=credentials["certificateId"],
                               forceDelete=True)
        os.remove(cert_path)
        os.remove(key_path)
        os.rmdir(credentials_dir)

    atexit.register(cleanup_credentials)


def get_test_info():
    """Retrieves the version of the ExpressLink tests"""
    # TODO: Create python tests versioning strategy
    test_info = {'test_version': "eltest-0.0.1", 'test_techspec': "v1.2"}
    return test_info


def get_optional_feature_args() -> list[str]:
    return []


if __name__ == "__main__":
    ts = datetime.now().isoformat().replace(':', '_')
    # Pytest json report parameters
    os.makedirs('./Test_Results', exist_ok=True)
    cf.pytest_args.extend(
        f"--json-report --json-report-indent=2 --json-report-file=./Test_Results/eltest_report_{ts}.json"
        .split())

    # TODO: Refactor main behavior into organized functions
    expresslink_info: dict[str, str] = {}
    expresslink_info['platform'] = cf.get('platform', str)
    expresslink_info.update(get_test_info())
    pytest.expresslink_info = expresslink_info

    # Turn on/off optional features
    cf.pytest_args += get_optional_feature_args()

    if '--collect-only' not in cf.pytest_args:
        iot = boto3.client("iot")
        with DeviceLib() as lib:
            lib.reset_device()
            pytest.expresslink_info.update(lib.get_device_info())

            generate_test_credentials()

            print(
                "\033[96mBeginning tests with the following parameters:\n\033[92m"
            )
            pprint(expresslink_info)
            print("\033[33m")
            pprint(cf.pytest_args)
            print("\033[0m")
            sys.exit(pytest.main(cf.pytest_args))
    else:
        sys.exit(pytest.main(cf.pytest_args))
