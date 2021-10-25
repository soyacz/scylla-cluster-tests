from invoke import Collection

import tasks.sample
import tasks.sct
from tasks.libs.persisted_dicts import FilePersistedDotDict

ns = Collection(tasks.sample, tasks.sct)
ns.configure({'persisted': FilePersistedDotDict("persisted_dict.json")})
