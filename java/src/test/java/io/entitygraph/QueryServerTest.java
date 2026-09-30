package io.entitygraph;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class QueryServerTest {
    @Test void acceptsStableIdentifier() { assertEquals("abcdef012345abcdef012345", QueryServer.entityId("id=abcdef012345abcdef012345")); }
    @Test void rejectsInjectionAndMissingInputs() {
        for (String query : new String[]{null, "", "id=' OR 1=1", "id=abc&x=1", "id=%ZZ"})
            assertThrows(IllegalArgumentException.class, () -> QueryServer.entityId(query));
    }
}
