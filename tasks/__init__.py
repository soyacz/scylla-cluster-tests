from invoke import Collection

import tasks.sample
import tasks.sct
from tasks.persisted_context import PersistedContext

ns = Collection(tasks.sample, tasks.sct)
ns.configure({'persisted': PersistedContext()})
