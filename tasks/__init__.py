from invoke import Collection

from scylla_arms.persisted_dicts import FilePersistedDotDict
import tasks.sct


ns = Collection(tasks.sct)
ns.configure({'persisted': FilePersistedDotDict("persisted_dict.json")})
