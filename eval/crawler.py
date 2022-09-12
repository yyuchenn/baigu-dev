from os.path import exists
from datetime import datetime
import requests
from repo_model import *


if not exists(db_filename):
    with db:
        db.create_tables([Repo])


headers = {"Authorization": "Bearer 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"}
query_template = '''query {
  search(
    query: "is:public language:Python stars:\\\"> 10\\\" created:YYYY1-MM1-DD1..YYYY2-MM2-DD2"
    type: REPOSITORY
    first: 100
    after: AFTER
  ) {
    edges {
      node {
        ... on Repository {
          id
          url
          isArchived
          stargazers {
            totalCount
          }
          defaultBranchRef {
            target {
              ... on Commit {
                pushedDate
              }
            }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
    repositoryCount
  }
}'''
yyyy = 2022
mm = 5
for p in range(12):  # 1032 2022-07
    YYYY1 = yyyy + (mm * 6 + p) // 72
    MM1 = ((mm * 6 + p) % 72) // 6 + 1
    DD1 = (p % 6) * 5 + 1
    YYYY2 = yyyy + (mm * 6 + p + 1) // 72
    MM2 = ((mm * 6 + p + 1) % 72) // 6 + 1
    DD2 = ((p + 1) % 6) * 5 + 1
    print(f"month {p:03d}: {YYYY1}-{MM1:02d}-{DD1:02d} to {YYYY2}-{MM2:02d}-{DD2:02d}")
    after = "null"
    hasNextPage = True
    query_ = query_template\
        .replace("YYYY1", str(YYYY1), 1).replace("MM1", str(MM1).zfill(2), 1).replace("DD1", str(DD1).zfill(2), 1)\
        .replace("YYYY2", str(YYYY2), 1).replace("MM2", str(MM2).zfill(2), 1).replace("DD2", str(DD2).zfill(2), 1)
    while hasNextPage:
        query = query_.replace("AFTER", after, 1)
        response = requests.post("https://api.github.com/graphql", json={"query": query}, headers=headers).json()
        if "errors" in response.keys():
            print(response["errors"])
            exit(-1)
        if response["data"]["search"]["repositoryCount"] == 0:
            break
        hasNextPage = response["data"]["search"]["pageInfo"]["hasNextPage"]
        after = '"' + response["data"]["search"]["pageInfo"]["endCursor"] + '"'

        with db.atomic():
            for entry in response["data"]["search"]["edges"]:
                date = entry["node"]["defaultBranchRef"]["target"]["pushedDate"]
                if date is not None:
                    date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
                r, _ = Repo.get_or_create(id_=entry["node"]["id"], url=entry["node"]["url"])
                r.star = entry["node"]["stargazers"]["totalCount"]
                r.archived = entry["node"]["isArchived"]
                r.pushedDate = date
                r.save()
