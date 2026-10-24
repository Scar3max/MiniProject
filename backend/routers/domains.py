"""
backend/routers/domains.py - Interview domain listing and metadata.
"""

from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/domains", tags=["domains"])


class DomainItem(BaseModel):
    id: str
    name: str
    icon: str
    description: str
    gradient: str


POPULAR_DOMAINS: List[dict] = [
    {
        "id": "python-programming",
        "name": "Python Programming",
        "icon": "🐍",
        "description": "Core syntax, memory model, decorators, generators, and async programming.",
        "gradient": "from-emerald-500 to-teal-600"
    },
    {
        "id": "data-structures",
        "name": "Data Structures and Algorithms",
        "icon": "📊",
        "description": "Arrays, linked lists, trees, graphs, sorting, searching, and dynamic programming.",
        "gradient": "from-purple-500 to-indigo-600"
    },
    {
        "id": "web-development",
        "name": "Web Development",
        "icon": "🌐",
        "description": "Frontend, backend, REST/GraphQL APIs, authentication, and browser mechanics.",
        "gradient": "from-amber-500 to-rose-600"
    },
    {
        "id": "cloud-computing",
        "name": "Cloud Computing",
        "icon": "☁️",
        "description": "Architecture, containers, serverless, microservices, and distributed deployments.",
        "gradient": "from-sky-400 to-cyan-600"
    },
    {
        "id": "machine-learning",
        "name": "Machine Learning",
        "icon": "🤖",
        "description": "Supervised, unsupervised models, neural architectures, evaluation, and tuning.",
        "gradient": "from-fuchsia-500 to-pink-600"
    },
    {
        "id": "operating-systems",
        "name": "Operating Systems",
        "icon": "💻",
        "description": "Process scheduling, thread concurrency, virtual memory, paging, and kernel I/O.",
        "gradient": "from-blue-500 to-cyan-600"
    },
    {
        "id": "computer-networks",
        "name": "Computer Networks",
        "icon": "🌍",
        "description": "OSI & TCP/IP stack, routing, DNS, HTTP/HTTPS, TLS, and transport protocols.",
        "gradient": "from-teal-500 to-emerald-600"
    },
    {
        "id": "database-management",
        "name": "Database Management Systems",
        "icon": "🗄️",
        "description": "ACID transactions, relational design, indexing, NoSQL, and query planning.",
        "gradient": "from-violet-500 to-purple-600"
    }
]


@router.get("", response_model=List[DomainItem])
async def list_domains():
    """Returns the popular interview domains available for instant practice."""
    return POPULAR_DOMAINS
