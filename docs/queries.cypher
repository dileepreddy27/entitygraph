// Mentions and original sources for a canonical organization.
MATCH (d:Document)-[:HAS_MENTION]->(m:Mention)-[:RESOLVES_TO]->(e:Entity)
WHERE e.name = 'Northstar Analytics'
RETURN d.id, m.text, m.start, m.end ORDER BY d.id, m.start;

// Payments with source document evidence. Amount is preserved as a decimal string.
MATCH (payer:Entity)-[:PAYER]->(t:Transaction)-[:PAYEE]->(payee:Entity),
      (d:Document)-[:EVIDENCES]->(t)
RETURN payer.name, payee.name, t.amount, t.currency, d.id;

// Co-occurrence only: shared sources do not assert employment or ownership.
MATCH (a:Entity)<-[:RESOLVES_TO]-(:Mention)<-[:HAS_MENTION]-(d:Document),
      (d)-[:HAS_MENTION]->(:Mention)-[:RESOLVES_TO]->(b:Entity)
WHERE a.id < b.id
RETURN a.name, b.name, count(DISTINCT d) AS sharedDocuments;
