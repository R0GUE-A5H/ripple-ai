UPSERT_CUSTOM_ASSERTION = """
mutation UpsertAssertion($input: UpsertCustomAssertionInput!) {
  upsertCustomAssertion(input: $input) {
    urn
  }
}
"""

REPORT_ASSERTION_RESULT = """
mutation ReportAssertion(
    $urn: String!,
    $result: AssertionResultInput!
){
  reportAssertionResult(
      urn:$urn,
      result:$result
  )
}
"""

FIND_ASSERTION = """
query FindAssertion($query: String!) {
  searchAcrossEntities(
    input: {
      types: [ASSERTION]
      query: $query
      count: 20
      start: 0
    }
  ) {
    searchResults {
      entity {
        urn
        ... on Assertion {
          info {
            description
          }
        }
      }
    }
  }
}
"""

CREATE_GLOSSARY_TERM = """
mutation CreateGlossaryTerm($input: CreateGlossaryEntityInput!) {
    createGlossaryTerm(input: $input)
}
"""

ADD_GLOSSARY_TERM = """
mutation AddTerm($input: TermAssociationInput!) {
    addTerm(input: $input)
}
"""

REMOVE_GLOSSARY_TERM = """
mutation RemoveTerm($input: TermAssociationInput!) {
    removeTerm(input: $input)
}
"""
