#!/usr/bin/env python

import datetime
import pytz
import time
from oauth2client.client import GoogleCredentials
from googleapiclient import discovery


def wait_for_operation(compute, project, zone, operation):
    debug('Waiting for operation to finish...')
    while True:
        result = compute.zoneOperations().get(
            project=project,
            zone=zone,
            operation=operation).execute()

        if result['status'] == 'DONE':
            if 'error' in result:
                raise Exception(result['error'])
            return result

        time.sleep(1)


def is_running(compute, project, zone, instance):
    result = compute.instances().get(project=project, zone=zone, instance=instance['name']).execute()
    if result['status'] == 'RUNNING':
        return True
    return False


def list_instances(compute, project, zone):
    alive_instances = []
    result = compute.instances().list(project=project, zone=zone).execute()
    if 'items' in result:
        for item in result['items']:
            if item['status'] == 'RUNNING':
                alive_instances.append(item)
            else:
                set_launch_time(compute, project, zone, item, "")
    return alive_instances


def debug(str):
    #    print(str)
    return


def keep_alive_instance(instance):
    # checking labels
    if 'labels' in instance:
        for key in instance['labels']:
            if key == 'keep' or key == 'keep-alive':
                debug(key)
                return True

    # checking tags
    if 'tags' not in instance or 'items' not in instance['tags']:
        return False
    for tag in instance['tags']['items']:
        debug(tag)
        if tag == 'alive' or tag == 'keep-alive' or tag == 'keep':
            return True
    return False


def set_launch_time(compute, project, zone, instance, launch_time):
    set = False
    instance = compute.instances().get(project=project, zone=zone, instance=instance['name']).execute()
    metadata = {}
    if 'metadata' in instance:
        metadata = instance['metadata']
        if 'items' in metadata:
            for item in metadata['items']:
                if item['key'] == "launch_time":
                    item['value'] = launch_time
                    set = True
        else:
            metadata['items'] = []
    else:
        metadata['items'] = []

    if not set:
        lt = {"key": "launch_time", "value": launch_time}
        metadata['items'].append(lt)

    request = compute.instances().setMetadata(project=project, zone=zone, instance=instance['name'], body=metadata)
    response = request.execute()
    wait_for_operation(compute, project, zone, operation=response['name'])


def get_launch_time(instance):
    metadata = {}
    if 'metadata' in instance:
        metadata = instance['metadata']
        if 'items' in metadata:
            for item in metadata['items']:
                if item['key'] == "launch_time":
                    return item['value']
    return None


def keep_instance(compute, project, zone, instance):
    keep = False

    # checking up time
    lt_datetime_str = get_launch_time(instance)
    if lt_datetime_str != None and lt_datetime_str != "":
        lt_datetime = datetime.datetime.strptime(lt_datetime_str, "%B %d, %Y, %H:%M:%S")
        lt_datetime = lt_datetime.replace(tzinfo=pytz.utc)
    else:
        lt_datetime = datetime.datetime.now(tz=pytz.utc)
        set_launch_time(compute, project, zone, instance, lt_datetime.strftime("%B %d, %Y, %H:%M:%S"))
    lt_delta = datetime.datetime.now(tz=pytz.utc) - lt_datetime
    hours = abs(lt_delta).total_seconds() / 3600.0
    if hours < 11:
        keep = True

    return keep


def print_instance(instance, msg):
    print("instance %s type %s launched at %s description %s %s" %
          (instance['name'], instance['machineType'], get_launch_time(instance), instance['id'], msg))


def stop_instance(compute, project, zone, instance):
    set_launch_time(compute, project, zone, instance, "")
    request = compute.instances().stop(project=project, zone=zone, instance=instance['name'], discardLocalSsd="true")
    response = request.execute()


def terminate_instance(compute, project, zone, instance):
    request = compute.instances().delete(project=project, zone=zone, instance=instance['name'])
    response = request.execute()


def check_zone(compute, project, zone):
    instances = list_instances(compute, project, zone)

    count_running = 0
    count_long_running = 0
    count_stopped = 0
    stopped_instances = []
    for instance in instances:
        debug(instance)
        debug("checking instance %s %s %s %s %s" %
              (instance['id'], instance['name'], instance['machineType'], instance['tags'], instance['zone']))
        ka = keep_alive_instance(instance)
        if ka or keep_instance(compute, project, zone, instance):
            if ka:
                count_long_running = count_long_running + 1
                print_instance(instance, "long running")
            count_running = count_running + 1
            debug("will not be stopped")
        else:
            count_stopped = count_stopped + 1
            stop_instance(compute, project, zone, instance)
            print_instance(instance, "stopped")
            stopped_instances.append(instance)
    # verifying instances are stopped - if they are not terminating them
    time.sleep(10)
    for instance in stopped_instances:
        if is_running(compute, project, zone, instance):
            terminate_instance(compute, project, zone, instance)
            print_instance(instance, "terminated")

    print("zone %s stopped %d instances, long running %d running %d instances" %
          (zone, count_stopped, count_long_running, count_running))


credentials = GoogleCredentials.get_application_default()
compute = discovery.build('compute', 'v1', credentials=credentials)

zones = ['asia-east1-a', 'asia-east1-b', 'asia-east1-c',
         'asia-northeast1-a', 'asia-northeast1-b', 'asia-northeast1-c',
         'europe-west1-b', 'europe-west1-c', 'europe-west1-d',
         'us-central1-a', 'us-central1-b', 'us-central1-c', 'us-central1-f',
         'us-east1-b', 'us-east1-c', 'us-east1-d',
         'us-west1-a', 'us-west1-b']

for zone in zones:
    check_zone(compute, 'skilled-adapter-452', zone)
