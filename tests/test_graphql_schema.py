"""Sanity checks for the Strawberry schema (no Supabase required)."""

import pytest
from app.graphql.schema import schema


def test_schema_introspection_has_auth_mutations():
    result = schema.execute_sync(
        """
        query {
          __schema {
            mutationType {
              fields {
                name
              }
            }
          }
        }
        """
    )
    assert result.errors is None
    names = {f["name"] for f in result.data["__schema"]["mutationType"]["fields"]}
    assert "signUp" in names
    assert "signIn" in names
    assert "saveFileAssociations" in names
    assert "refreshSession" in names
    assert "establishSession" in names
    assert "clearSession" in names
    assert "updateAiProviderSettings" in names
    assert "chatCompletion" in names


def test_schema_has_chat_query_fields():
    result = schema.execute_sync(
        """
        query {
          __schema {
            queryType {
              fields {
                name
              }
            }
          }
        }
        """
    )
    assert result.errors is None
    names = {f["name"] for f in result.data["__schema"]["queryType"]["fields"]}
    assert "me" in names
    assert "emailRegistered" in names
    assert "chatProviders" in names
    assert "systemHealth" in names
    assert "weatherForecast" in names
    assert "ragStats" in names
    assert "aiProviderSettings" in names
    assert "websocketGatewayStatus" in names
    assert "storageSignedHttpUrl" in names
    assert "hostStats" in names
    assert "libraryBooks" in names


def test_gql_user_type_exposes_profile_fields():
    result = schema.execute_sync(
        """
        query {
          gqlUser: __type(name: "GqlUser") {
            fields {
              name
            }
          }
          gqlUserProfile: __type(name: "GqlUserProfile") {
            fields {
              name
            }
          }
        }
        """
    )
    assert result.errors is None
    user_fields = {f["name"] for f in result.data["gqlUser"]["fields"]}
    assert "profile" in user_fields
    assert "isActive" in user_fields
    assert "isVerified" in user_fields
    assert "updatedAt" in user_fields
    prof_fields = {f["name"] for f in result.data["gqlUserProfile"]["fields"]}
    assert "username" in prof_fields
    assert "avatarUrl" in prof_fields


@pytest.mark.asyncio
async def test_host_stats_resolver():
    result = await schema.execute(
        """
        query {
          hostStats
        }
        """
    )
    assert result.errors is None
    stats = result.data["hostStats"]
    assert "cpu" in stats
    assert "ram" in stats
    assert "storage" in stats
    assert "network" in stats
