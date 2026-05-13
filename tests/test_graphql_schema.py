"""Sanity checks for the Strawberry schema (no Supabase required)."""

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
    assert "refreshSession" in names
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
