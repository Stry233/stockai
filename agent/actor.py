

import numpy as np
import time

from .replay_buffer import LocalBuffer
from env import Env


class Actor:

    def __init__(self,
                 learner_rref,
                 tickers,
                 d_model,
                 state_len
                 ):
        np.random.seed(0)

        self.learner_rref = learner_rref

        self.d_model = d_model
        self.state_len = state_len

        self.env = Env(tickers=tickers,
                       render=False,
                       start="2020-01-01",  # 2010
                       end="2021-01-01",
                       repeat=1
                       )

        self.local_buffer = LocalBuffer()

    def get_action(self, alloc, timestamp, tickers, state):
        """
        :param alloc:     float
        :param timestamp: datetime.datetime
        :param tickers:   List[2]
        :param state:     Array[1. state_len, d_model]
        :return:
            Future(
                 action:  float
                 state:   Array[1, state_len, d_model]
            )
        """
        future_action = self.learner_rref.rpc_async().queue_request(alloc,
                                                                    timestamp,
                                                                    tickers,
                                                                    state
                                                                    )
        return future_action

    def return_episode(self, episode):
        """
        sends completed episode back to learner
        """
        self.learner_rref.rpc_async().return_episode(episode)

    def run(self):

        while True:
            (alloc, timestamp), total_reward, done, tickers = self.env.reset()
            state = np.zeros((1, self.state_len, self.d_model), dtype=np.float32)

            start = time.time()
            while not done:
                action, new_state = self.get_action(alloc, timestamp, tickers, state).wait()

                (new_alloc, new_timestamp), reward, done, tickers = self.env.step(action)

                self.local_buffer.add(alloc, timestamp, action, reward, state)

                alloc = new_alloc
                timestamp = new_timestamp
                state = new_state

                total_reward += reward

            episode = self.local_buffer.finish(tickers, total_reward, time.time()-start)
            self.return_episode(episode)

            self.env.render_episode()
