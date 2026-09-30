package io.entitygraph;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import org.neo4j.driver.AuthTokens;
import org.neo4j.driver.GraphDatabase;

/** Read-only local evidence API. No arbitrary Cypher is accepted. */
public final class QueryServer {
    public static String entityId(String query) {
        if (query == null || !query.startsWith("id=") || query.contains("&"))
            throw new IllegalArgumentException("Expected one id parameter");
        String id = URLDecoder.decode(query.substring(3), StandardCharsets.UTF_8);
        if (!id.matches("[a-f0-9]{24}")) throw new IllegalArgumentException("Invalid entity id");
        return id;
    }

    public static void main(String[] args) throws Exception {
        String password = System.getenv("NEO4J_PASSWORD");
        if (password == null || password.isBlank()) throw new IllegalArgumentException("Set NEO4J_PASSWORD");
        var driver = GraphDatabase.driver(System.getenv().getOrDefault("NEO4J_URI", "bolt://localhost:7687"),
                AuthTokens.basic(System.getenv().getOrDefault("NEO4J_USER", "neo4j"), password));
        driver.verifyConnectivity();
        var mapper = new ObjectMapper();
        var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 8080), 0);
        server.createContext("/entities", exchange -> {
            int status = 200;
            Object payload;
            try {
                if (!exchange.getRequestMethod().equals("GET")) {
                    status = 405; payload = Map.of("error", "GET required");
                } else if (!exchange.getRequestURI().getPath().equals("/entities")) {
                    status = 404; payload = Map.of("error", "Not found");
                } else {
                    String query = exchange.getRequestURI().getRawQuery();
                    try (var session = driver.session()) {
                        if (query == null) {
                            payload = session.executeRead(tx -> tx.run("MATCH (e:Entity) RETURN e ORDER BY e.name LIMIT 100")
                                    .list(r -> r.get("e").asNode().asMap()));
                        } else {
                            String id = entityId(query);
                            payload = session.executeRead(tx -> tx.run("MATCH (d:Document)-[:HAS_MENTION]->(m:Mention)-[:RESOLVES_TO]->(e:Entity {id:$id}) RETURN d.id AS document, m.text AS text, m.start AS start, m.end AS end ORDER BY document, start LIMIT 100", Map.of("id", id))
                                    .list(r -> r.asMap()));
                        }
                    }
                }
            } catch (IllegalArgumentException ex) {
                status = 400; payload = Map.of("error", "Invalid query; expected id with 24 lowercase hexadecimal characters");
            } catch (Exception ex) {
                status = 503; payload = Map.of("error", "Graph unavailable");
            }
            byte[] body = mapper.writeValueAsBytes(payload);
            exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
            exchange.sendResponseHeaders(status, body.length);
            try (var out = exchange.getResponseBody()) { out.write(body); }
        });
        Runtime.getRuntime().addShutdownHook(new Thread(() -> { server.stop(0); driver.close(); }));
        server.start();
        System.out.println("EntityGraph query API: http://127.0.0.1:8080/entities");
    }
}
