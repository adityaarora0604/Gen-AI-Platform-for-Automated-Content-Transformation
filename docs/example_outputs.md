# Example outputs (DEMO MODE)

> These were produced by running `sample_data/sample_advisory_source.txt` through the platform with `LLM_PROVIDER=demo`.
> They are **rule-based extracts, not AI-generated text**, and are included only to show the exact structure each format follows.
> With `LLM_PROVIDER=anthropic` the same sections are written by the model in the requested tone, audience and language.

## Structured source representation

```json
{
  "summary": "On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its AcmeVPN Gateway product. The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.",
  "key_points": [
    "On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its AcmeVPN Gateway product.",
    "The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.",
    "According to the vendor, about 3,500 organisations use the affected versions.",
    "The company reported that 12% of these deployments are exposed directly to the internet.",
    "Researchers at Northwind Labs said they observed exploitation attempts beginning on 10 March 2026, although the activity has not been attributed to any specific group and the claim remains unconfirmed.",
    "AcmeCorp released version 4.9 on 14 March 2026, which fixes the flaw."
  ],
  "facts": [
    "On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its AcmeVPN Gateway product.",
    "According to the vendor, about 3,500 organisations use the affected versions.",
    "The company reported that 12% of these deployments are exposed directly to the internet.",
    "AcmeCorp released version 4.9 on 14 March 2026, which fixes the flaw.",
    "The vendor recommends that administrators update to version 4.9 immediately and restrict management interfaces to trusted networks.",
    "Organisations should also review gateway logs for unusual login activity since 1 March 2026."
  ],
  "entities": [
    "CVE-2026-12345",
    "AcmeCorp",
    "AcmeVPN Gateway",
    "Northwind Labs"
  ],
  "dates": [
    "12 March 2026",
    "10 March 2026",
    "14 March 2026",
    "1 March 2026"
  ],
  "important_figures": [
    "3,500 organisations",
    "12%"
  ],
  "caveats": [
    "The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.",
    "Researchers at Northwind Labs said they observed exploitation attempts beginning on 10 March 2026, although the activity has not been attributed to any specific group and the claim remains unconfirmed.",
    "The full extent of the impact is still under investigation.",
    "It is not yet known whether any customer data was accessed."
  ],
  "source_language": "English"
}
```

## Executive Summary

```markdown
[DEMO MODE: rule-based extract from the source, NOT AI-generated]

# On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its A…
## Overview
On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its AcmeVPN Gateway product. The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.
## Key Findings
- On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its AcmeVPN Gateway product.
- The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.
- According to the vendor, about 3,500 organisations use the affected versions.
- The company reported that 12% of these deployments are exposed directly to the internet.
- Researchers at Northwind Labs said they observed exploitation attempts beginning on 10 March 2026, although the activity has not been attributed to any specific group and the claim remains unconfirmed.
## Important Facts
- On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its AcmeVPN Gateway product.
- According to the vendor, about 3,500 organisations use the affected versions.
- The company reported that 12% of these deployments are exposed directly to the internet.
- AcmeCorp released version 4.9 on 14 March 2026, which fixes the flaw.
- The vendor recommends that administrators update to version 4.9 immediately and restrict management interfaces to trusted networks.
## Conclusion
The source points summarised above are the findings it supports. Caveat noted in the source: The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.
```

Validation warnings: none

## LinkedIn Post

```markdown
[DEMO MODE: rule-based extract from the source, NOT AI-generated]

## Hook
On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its AcmeVPN Gateway product.
## Post
On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its AcmeVPN Gateway product. The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.
## Key Takeaways
- The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.
- According to the vendor, about 3,500 organisations use the affected versions.
- The company reported that 12% of these deployments are exposed directly to the internet.
- Researchers at Northwind Labs said they observed exploitation attempts beginning on 10 March 2026, although the activity has not been attributed to any specific group and the claim remains unconfirmed.
- AcmeCorp released version 4.9 on 14 March 2026, which fixes the flaw.
## Hashtags
#Cve202612345 #Acmecorp #AcmevpnGateway #NorthwindLabs
## Call to Action
Share this with your team and review your exposure today.
```

Validation warnings: none

## X (Twitter) Post / Thread

```markdown
[DEMO MODE: rule-based extract from the source, NOT AI-generated]

1/5 On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its AcmeVPN Gateway product. The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.

2/5 On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its AcmeVPN Gateway product.

3/5 The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.

4/5 According to the vendor, about 3,500 organisations use the affected versions.

5/5 The company reported that 12% of these deployments are exposed directly to the internet.
```

Validation warnings: none

## Advisory

```markdown
[DEMO MODE: rule-based extract from the source, NOT AI-generated]

# Advisory: On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its A…
## Severity / Priority
Not specified in the source.
## Background
On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its AcmeVPN Gateway product. The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.
## Key Observations
- On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its AcmeVPN Gateway product.
- The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.
- According to the vendor, about 3,500 organisations use the affected versions.
- The company reported that 12% of these deployments are exposed directly to the internet.
- Researchers at Northwind Labs said they observed exploitation attempts beginning on 10 March 2026, although the activity has not been attributed to any specific group and the claim remains unconfirmed.
## Potential Impact
- The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.
- According to the vendor, about 3,500 organisations use the affected versions.
- The company reported that 12% of these deployments are exposed directly to the internet.
- According to the vendor, about 3,500 organisations use the affected versions.
- The company reported that 12% of these deployments are exposed directly to the internet.
## Recommended Actions
- The vendor recommends that administrators update to version 4.9 immediately and restrict management interfaces to trusted networks.
- Organisations should also review gateway logs for unusual login activity since 1 March 2026.
## Caveats
- The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.
- Researchers at Northwind Labs said they observed exploitation attempts beginning on 10 March 2026, although the activity has not been attributed to any specific group and the claim remains unconfirmed.
- The full extent of the impact is still under investigation.
- It is not yet known whether any customer data was accessed.
- This advisory was generated automatically and has not been verified; human review is required.
```

Validation warnings: none

## Presentation Content

```markdown
[DEMO MODE: rule-based extract from the source, NOT AI-generated]

# On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its A…
## Slide 1: Overview
- On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its AcmeVPN Gateway product. The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker…
**Suggested visual:** Title graphic or cover image
**Speaker notes:** Introduce the topic using the overview above.
## Slide 2: Key Points
- On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its AcmeVPN Gateway product.
- The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.
- According to the vendor, about 3,500 organisations use the affected versions.
- The company reported that 12% of these deployments are exposed directly to the internet.
- Researchers at Northwind Labs said they observed exploitation attempts beginning on 10 March 2026, although the activity has not been attributed to any specific group and the claim remains unconfirme…
**Suggested visual:** Icon list or numbered diagram
**Speaker notes:** Walk through each key point in order.
## Slide 3: Facts and Figures
- On 12 March 2026, AcmeCorp announced a vulnerability, tracked as CVE-2026-12345, in its AcmeVPN Gateway product.
- According to the vendor, about 3,500 organisations use the affected versions.
- The company reported that 12% of these deployments are exposed directly to the internet.
- AcmeCorp released version 4.9 on 14 March 2026, which fixes the flaw.
- The vendor recommends that administrators update to version 4.9 immediately and restrict management interfaces to trusted networks.
**Suggested visual:** Table or bar chart of the figures
**Speaker notes:** Read out the exact figures and where they come from in the source.
## Slide 4: Caveats and Limits
- The flaw affects versions 4.2 through 4.8 and could allow an unauthenticated attacker to execute arbitrary commands on the device.
- Researchers at Northwind Labs said they observed exploitation attempts beginning on 10 March 2026, although the activity has not been attributed to any specific group and the claim remains unconfirme…
- The full extent of the impact is still under investigation.
- It is not yet known whether any customer data was accessed.
**Suggested visual:** Warning callout box
**Speaker notes:** State clearly what is uncertain or unconfirmed.
```

Validation warnings: none
