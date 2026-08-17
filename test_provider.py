from search_engine.providers.remoteok_provider import RemoteOKProvider

provider = RemoteOKProvider()
jobs = provider.search()

print("Type:", type(jobs))
print("Jobs:", len(jobs))

for job in jobs[:5]:
    print(job)

