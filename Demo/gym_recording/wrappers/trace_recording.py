import os
import time
import json
import glob
import logging
import cv2
import numpy as np
import Demo_gym
from Demo_gym import error
from Demo_gym.utils import closer
from gym_recording.recording import TraceRecording
logger = logging.getLogger(__name__)

__all__ = ['TraceRecordingWrapper']


trace_record_closer = closer.Closer()

class TraceRecordingWrapper(Demo_gym.Wrapper):
    """

    A Wrapper that records a trace of every action, observation, and reward generated by an environment.
    For an episode of length N, this will consist of:
      actions [0..N]
      observations [0..N+1]. Including the initial observation from `env.reset()`
      rewards [0..N]

    Usage:

      from gym_recording.wrappers import TraceRecordingWrapper
      if args.record_trace:
        env = TraceRecordingWrapper(env, '/tmp/mytraces')

    It'll save a numbered series of json-encoded files, with large arrays stored in binary, along
    with a manifest in /tmp/mytraces/openaigym.traces.*.
    See gym_recording.recording for more on the file format

    Later you can load the recorded traces:

      import gym_recording.playback

      def episode_cb(observations, actions, rewards):
          ... do something the episode ...

      gym_recording.playback.scan_recorded_traces('/tmp/mytraces', episode_cb)

    For an episode of length N, episode_cb receives 3 numpy arrays:
      observations.shape = [N + 1, observation_dim]
      actions.shape = [N, action_dim]
      rewards.shape = [N]


    """
    def __init__(self, env, directory=None):
        """
        Create a TraceRecordingWrapper around env, writing into directory
        """
        super(TraceRecordingWrapper, self).__init__(env)
        self.recording = None
        trace_record_closer.register(self)

        self.recording = TraceRecording(None)
        self.directory = self.recording.directory

    def _step(self, action):
        observation, reward, done, info = self.env.step(action)
        RGB_observation = cv2.cvtColor(observation, cv2.COLOR_BGR2RGB)
        #cv2.imshow('',RGB_img)
        #cv2.waitKey(1)
        self.recording.add_step(action, RGB_observation, reward)
        return observation, reward, done, info

    def _reset(self):
        self.recording.end_episode()
        observation = self.env.reset()
        self.recording.add_reset(observation)
        return observation

    def close(self):
        """
        Flush any buffered data to disk and close. It should get called automatically at program exit time, but
        you can free up memory by calling it explicitly when you're done
        """
        if self.recording is not None:
            self.recording.close()
