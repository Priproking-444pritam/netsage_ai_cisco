# NetSage AI — Few-Shot Examples

These three worked examples are appended to `diagnose_prompt.md` (as prior
turns) before every real case is sent to the model. They were chosen to
cover three different OSI layers and three different confidence levels, so
the model sees what "Low" honest uncertainty looks like, not just confident
answers.

---

## Example 1 — High confidence, Layer 2 (VLAN)

**Input**
```
CASE ID: EX-01
CATEGORY: VLAN
SYMPTOM: PC1 (VLAN 10) cannot ping PC2, both on switch SW1, same subnet.
TOPOLOGY NOTE: SW1 Fa0/2->PC1, Fa0/3->PC2. Both should be VLAN 10.
SHOW OUTPUT:
SW1# show vlan brief | VLAN10 ACCTG active Fa0/2 | VLAN20 SALES active Fa0/3
```

**Expected Output**
```json
{
  "root_cause": "PC2's switch port (Fa0/3) is assigned to VLAN 20 instead of VLAN 10, so it is on a different broadcast domain than PC1.",
  "osi_layer": "L2",
  "confidence": "High",
  "evidence": "show vlan brief lists Fa0/3 under VLAN20 SALES, not VLAN10 ACCTG where Fa0/2 (PC1) sits.",
  "next_command": "show running-config interface Fa0/3",
  "fix_steps": "On SW1, enter interface Fa0/3 and run 'switchport access vlan 10' to move PC2 into VLAN 10, then verify with 'show vlan brief'."
}
```

---

## Example 2 — Medium confidence, Layer 3 (Routing)

**Input**
```
CASE ID: EX-02
CATEGORY: Routing
SYMPTOM: R1 and R2 are RIP neighbors, but hosts on R2's LAN cannot be reached from R1's LAN.
TOPOLOGY NOTE: RIP version 2 running between R1 and R2.
SHOW OUTPUT:
R2# show run | router rip | version 2 | network 10.0.0.0 (192.168.20.0 network statement missing)
```

**Expected Output**
```json
{
  "root_cause": "R2 is not advertising its own LAN network (192.168.20.0) into RIP, so R1 never learns a route to it.",
  "osi_layer": "L3",
  "confidence": "Medium",
  "evidence": "R2's RIP configuration only shows a 'network 10.0.0.0' statement; no network statement for 192.168.20.0 is present.",
  "next_command": "show ip route rip",
  "fix_steps": "On R2, under router rip, add 'network 192.168.20.0' so the LAN is advertised, then confirm R1 learns the route with 'show ip route rip'."
}
```
*(Confidence is Medium, not High, because the routing table itself hasn't
been checked yet to confirm the route is truly absent on R1 — the missing
network statement is strong but indirect evidence.)*

---

## Example 3 — Low confidence, ambiguous evidence (Wireless)

**Input**
```
CASE ID: EX-03
CATEGORY: Wireless
SYMPTOM: Wireless clients near two APs experience high latency and frequent disconnects in the overlap zone.
TOPOLOGY NOTE: AP1 and AP2 cover adjoining rooms with overlapping coverage.
SHOW OUTPUT:
AP1# show interface dot11radio0 | Channel: 6 || AP2# show interface dot11radio0 | Channel: 6
```

**Expected Output**
```json
{
  "root_cause": "Both APs are broadcasting on the same 2.4GHz channel (6) in an overlapping coverage area, which is consistent with co-channel interference, though signal strength/interference readings have not been captured yet.",
  "osi_layer": "L1",
  "confidence": "Low",
  "evidence": "AP1 and AP2 both report Channel: 6 on dot11radio0.",
  "next_command": "show interface dot11radio0 statistics",
  "fix_steps": "Move AP2 to a non-overlapping channel (e.g. 1 or 11) and monitor client disconnect rate before confirming the fix resolved the issue."
}
```
*(Confidence is Low: same-channel APs are a strong hint, but the show
output alone can't rule out other causes of latency such as interference
from non-Wi-Fi devices or a bandwidth-saturated uplink.)*

---

## Why these three

- Example 1 shows a case where the evidence is unambiguous — the model
  should commit to High confidence and a precise fix.
- Example 2 shows the model correctly separating "strong indirect evidence"
  from "confirmed" — Medium confidence, and a next_command that would
  confirm it.
- Example 3 teaches the model to say "I'm not fully sure" out loud instead
  of dressing up a guess as certainty. This is the pattern reviewers look
  for when deciding Accept vs. Edit vs. Reject (see `review_log.csv`).
