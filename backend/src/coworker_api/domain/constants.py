"""
Shared domain constants for Edtronaut AI Coworker.
"""

# Chat persona display mapping — single source of truth.
# Used by both REST routes and gRPC server to validate NPC IDs.
NPC_ROLES: dict[str, str] = {
    "gucci_ceo": "Chief Executive Officer, Gucci",
    "gucci_chro": "Chief Human Resources Officer, Gucci",
    "gucci_eb_ic": "Investment Banker & Individual Contributor, Gucci Group Finance",
}
