# Responsible AI Log — NetSage AI

This log records every case where the AI's diagnosis was corrected by a human
reviewer, why the AI got it wrong, and what the reviewer changed.
A human review gate blocks every AI diagnosis from being marked as the final
answer until a reviewer explicitly accepts, edits, or rejects it.

**Total cases reviewed:** 32  
**Corrected by a human (Edited or Rejected):** 6  
**AI/human agreement rate:** 81.2%

---

## C003 — VLAN (Edited)

- **AI diagnosis:** Trunk not carrying VLAN 30 between SW1 and SW2 (allowed-VLAN list issue)
- **Actual root cause:** Native VLAN mismatch between trunk ends (SW1=1, SW2=99)
- **Why the AI got it wrong / what the reviewer changed:** AI focused on the allowed-VLAN list and missed the explicit CDP native-VLAN mismatch warning in the evidence. Reviewer corrected root cause to 'native VLAN mismatch' and pointed the fix at matching native VLAN on both trunk ends.

## C007 — Gateway (Edited)

- **AI diagnosis:** DHCP server assigned an incorrect gateway option to PC3
- **Actual root cause:** Typo: PC3's configured gateway (.254) does not match the router's actual sub-interface IP (.1)
- **Why the AI got it wrong / what the reviewer changed:** PC3's gateway was statically set, not DHCP-assigned, so the AI's DHCP theory was never testable against the evidence. Reviewer corrected the root cause to a manual gateway typo (.254 vs the router's real .1) after checking PC3's config mode.

## C012 — DHCP (Edited)

- **AI diagnosis:** DHCP pool for VLAN 10 is exhausted (no addresses available)
- **Actual root cause:** DHCP excluded-address range does not include the gateway .1, so it gets leased out to a client
- **Why the AI got it wrong / what the reviewer changed:** AI pattern-matched this to the more common 'pool exhausted' case (C009) instead of reading the actual excluded-address range in the evidence. Reviewer rejected the pool-exhaustion theory and corrected it to a missing gateway exclusion, which is a more serious IP-conflict risk, not just a capacity issue.

## C020 — Routing (Edited)

- **AI diagnosis:** Missing static route on R1 for the 172.16.20.0/24 network
- **Actual root cause:** Recursive routing failure: the next-hop 172.16.10.2 is itself unreachable, so the static route never resolves
- **Why the AI got it wrong / what the reviewer changed:** A route to 172.16.20.0/24 does exist in the table, so 'missing route' was not accurate. Reviewer corrected the diagnosis to a recursive routing failure: the route's next-hop is itself unreachable, so it never resolves to an exit interface.

## C024 — ACL (Rejected)

- **AI diagnosis:** NAT overload not translating return traffic from the web server
- **Actual root cause:** ACL 140 is missing a permit for established/return traffic, so reply packets from the server are dropped
- **Why the AI got it wrong / what the reviewer changed:** No NAT is involved in this topology at all; the AI pattern-matched 'replies not coming back' to a NAT issue from a similar past case. Reviewer rejected this and identified the real cause in ACL 140, which lacks a permit for established/return traffic.

## C030 — Wireless (Rejected)

- **AI diagnosis:** Wireless channel overlap causing dropped guest sessions
- **Actual root cause:** Guest VLAN 50 was never created/trunked correctly, so guest traffic falls back onto the native/internal VLAN
- **Why the AI got it wrong / what the reviewer changed:** This is a security-relevant misconfiguration (guest traffic reaching internal servers), not a performance issue, and the AI's channel-overlap theory does not explain guest devices reaching internal file servers at all. Reviewer rejected the AI output outright and escalated as a Responsible-AI flag: an AI system should not be trusted to self-certify security-boundary issues without a human check, since a wrong 'root cause' here could leave a real security gap unresolved.

---

## Takeaways

- The AI is prone to **pattern-matching to the most common fault in a category**
  (e.g. defaulting to 'pool exhausted' for any DHCP symptom) rather than reading
  the specific evidence in front of it — see C012.
- The AI can **miss evidence it wasn't specifically prompted to weigh**, such as a
  CDP warning line sitting next to the data it focused on — see C003.
- Security-relevant misdiagnoses (C030) are treated as the highest-priority
  category of error: a wrong root cause here doesn't just waste time, it can leave
  a real security exposure open. These are always routed to Rejected, never Edited.
- No AI diagnosis is surfaced to a junior engineer as a final answer without a
  human reviewer explicitly setting its status to Accepted.