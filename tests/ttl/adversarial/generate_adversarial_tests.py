from pathlib import Path

BASE = Path("tests/ttl/adversarial")
BASE.mkdir(parents=True, exist_ok=True)

PREFIX = """@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:   <http://example.org/> .

"""

def write(name, body):
    (BASE / name).write_text(PREFIX + body)

# Range explosion
for i in range(5):
    write(f"count_range_{i}.ttl", f"""
# EXPECTED: CONFLICT
ex:policy a odrl:Set ;
  odrl:permission [
    odrl:action odrl:use ;
    odrl:constraint [ odrl:leftOperand odrl:count ; odrl:operator odrl:lt ; odrl:rightOperand "{i}" ] ;
    odrl:constraint [ odrl:leftOperand odrl:count ; odrl:operator odrl:gt ; odrl:rightOperand "{i+10}" ]
  ] .
""")

# OR stress
write("or_deep.ttl", """
# EXPECTED: POSSIBLY-COMPATIBLE
ex:policy a odrl:Set ;
  odrl:permission [
    odrl:action odrl:use ;
    odrl:constraint [
      odrl:or (
        [ odrl:leftOperand odrl:count ; odrl:operator odrl:eq ; odrl:rightOperand "1" ]
        [ odrl:leftOperand odrl:count ; odrl:operator odrl:eq ; odrl:rightOperand "2" ]
        [ odrl:leftOperand odrl:count ; odrl:operator odrl:eq ; odrl:rightOperand "3" ]
      )
    ]
  ] .
""")

print("✔ Adversarial TTL tests generated")
