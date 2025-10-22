"""
Repository Indexing Example

This example demonstrates the repository indexing workflow that fetches
and indexes repositories from GitHub.
"""

import asyncio
from datetime import timedelta
from temporalio.client import Client


async def main():
    """Run the repository indexing example."""
    
    # Connect to Temporal server
    client = await Client.connect("localhost:7233")
    
    # Example repository data
    repo_data = {
        "remote_url": "https://github.com/octocat/Hello-World.git",
        "name": "Hello-World",
        "owner": "octocat",
        "branch": "master",
        "is_private": False,
        "credentials": None
    }
    
    print("Repository Indexing Example")
    print("===========================")
    print(f"Repository: {repo_data['owner']}/{repo_data['name']}")
    print(f"URL: {repo_data['remote_url']}")
    print(f"Branch: {repo_data['branch']}")
    print()
    
    try:
        # Run the workflow
        result = await client.execute_workflow(
            "RepositoryIndexingWorkflow",
            repo_data,
            id=f"repo-{repo_data['owner']}-{repo_data['name']}-{asyncio.get_event_loop().time()}",
            task_queue="repository-indexing-task-queue",
            execution_timeout=timedelta(hours=1)
        )
        
        print(f"✅ Successfully indexed repository!")
        print(f"   Status: {result['status']}")
        print(f"   Files processed: {result['files_processed']}")
        print(f"   Execution time: {result['execution_time_ms']}ms")
        
        if result['repository_index']:
            repo_index = result['repository_index']
            print(f"   Repository ID: {repo_index['repository_id']}")
            print(f"   Commit hash: {repo_index['commit_hash']}")
            print(f"   Total lines: {repo_index['total_lines']}")
            print(f"   Languages: {repo_index['languages']}")
        
        if result.get('saved_repo_id'):
            print(f"   Saved to database with ID: {result['saved_repo_id']}")
        
    except Exception as e:
        print(f"❌ Failed to index repository: {e}")


if __name__ == "__main__":
    asyncio.run(main())