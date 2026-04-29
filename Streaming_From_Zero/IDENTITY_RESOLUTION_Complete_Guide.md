# Identity Resolution in MarTech — Complete Guide
## From Zero to Expert | Costco Sr. Data Engineer Interview Prep
### "How do companies uniquely identify a person and target ads whether logged in or not?"

---

# WHY THIS PROBLEM IS HARD — START HERE

```
JOHN SMITH'S DEVICES:
  iPhone (Safari, sometimes logged in to Costco app)
  MacBook (Chrome, usually NOT logged in)
  iPad (Firefox, never logged in)
  Smart TV (Costco app, always logged in)
  Work laptop (Edge, never logged in)

JOHN'S JOURNEY IN ONE DAY:
  8:00 AM  → Sees Costco ad on iPhone (NOT logged in) → clicks → doesn't buy
  12:00 PM → Opens Chrome on MacBook → searches "Costco membership price"
             (System has NO IDEA this is the same John)
  7:00 PM  → Opens Costco iPad app → LOGS IN → views membership page
             (NOW we know: this is member M001234)
  9:00 PM  → MacBook → searches again → BUYS membership (logs in via Google SSO)

QUESTIONS THIS RAISES:
  Which ad gets credit for the sale?
  Was the 8 AM iPhone click the start of John's journey?
  Can you connect the anonymous 8 AM click to the 9 PM purchase?
  Can you stop showing John the membership ad AFTER he bought?

WITHOUT identity resolution: each device = a DIFFERENT unknown person.
WITH identity resolution:    all devices = ONE person = John Smith M001234.

THIS IS THE IDENTITY RESOLUTION PROBLEM.
```

---

# CHAPTER 1: THE BUILDING BLOCKS OF IDENTITY

## 1.1 Every Identifier Explained Simply

### DETERMINISTIC IDENTIFIERS — 100% certain

```
Deterministic = you KNOW with certainty this ID belongs to this person.
Why? Because the person TOLD YOU. They logged in. They authenticated.

1. MEMBER ID
   What:    Your internal unique ID (assigned when someone creates an account)
   Example: member_id = "M001234"
   When:    Only when user is LOGGED IN
   Why best: YOUR data, YOUR control, never changes, GDPR compliant

2. EMAIL ADDRESS (always stored as hash)
   What:    The email used to register
   Example: SHA256("john.smith@gmail.com") = "a8f3b2..."
   Use:     "Customer Match" — upload hashed emails to Google/Meta for targeting
   Rule:    NEVER send raw email to ad platforms. Always SHA256 hash first.

3. PHONE NUMBER (always stored as hash)
   Same concept as email. SHA256 before sharing.

WHY DETERMINISTIC IDs ARE THE GOLD STANDARD:
  No guessing. 100% certain. Privacy compliant.
  Downside: only available when user logs in (~20-40% of sessions).
```

### PROBABILISTIC IDENTIFIERS — educated guesses

```
Probabilistic = you are GUESSING based on signals.
Confidence: 60-95%. Never 100%.

4. IP ADDRESS
   What:    Network address of the device
   Example: 192.168.1.45
   Confidence: MEDIUM
   Problem: Multiple devices in same house share one IP.
            Millions share corporate/university/VPN IPs.
            Changes when user switches WiFi ↔ 4G.

5. BROWSER FINGERPRINT
   What:    A hash built from many browser properties combined
   Properties used:
     - Browser type and version (Chrome 121)
     - Operating system (macOS 14.2)
     - Screen resolution (2560×1600)
     - Installed fonts (list of 40+ fonts)
     - Canvas rendering (how browser draws a specific shape — pixel unique)
     - WebGL rendering (your graphics card's rendering pattern)
     - Timezone, language settings
     - CPU cores, memory size
   
   Combined → hash: "a7b3c9d2e1f4..."
   
   Confidence: HIGH (~95% unique to a specific browser on a specific device)
   Problem: Changes when browser or OS updates.
   Problem: Privacy browsers (Firefox, Brave) actively BLOCK fingerprinting.

6. DEVICE ADVERTISING ID
   iOS:     IDFA (Identifier for Advertisers)
   Android: GAID (Google Advertising ID)
   Example: "A1B2C3D4-E5F6-7890-ABCD-EF1234567890"
   
   These are like "license plates" for mobile devices — unique per device.
   
   THE BIG CHANGE (Apple ATT, 2021):
   Before: IDFA automatically available to all apps.
   After:  App MUST ask user permission. ~80% of users DECLINE.
   Result: IDFA is now unavailable for most iOS users.
   This is a major disruption to mobile ad targeting.
```

### THE COOKIE — web browser's anonymous ID

```
FIRST-PARTY COOKIE (still works, very important):
  Set by: the website you are visiting (costco.com)
  Contains: anonymous_id = "anon_xyz789"
  Duration: until user clears cookies or cookie expires
  Scope: only visible to costco.com
  
  THIS IS HOW COSTCO TRACKS ANONYMOUS USERS ON ITS OWN SITE.

THIRD-PARTY COOKIE (DYING):
  Set by: a DIFFERENT website than the one you're visiting
  Example: You visit cnn.com. Google Ads (a third party) sets a cookie.
           Next time you visit costco.com, Google reads that same cookie.
           This is how ads "follow you" across the web.
  
  STATUS: Chrome deprecating in 2024-2025. Safari/Firefox already block.
  IMPACT: The ENTIRE cross-web tracking industry was built on third-party cookies.
          Their death is forcing a fundamental shift to first-party data.

SIMPLE RULE:
  First-party cookie = on YOUR site = STILL WORKS
  Third-party cookie = across the web = DYING
```

---

## 1.2 The Anonymous ID — The Foundation of Everything

```
WHAT IS AN ANONYMOUS ID?

When a user visits your website or app for the FIRST TIME without logging in:

Step 1: Browser has NO Costco cookie → "new visitor"
Step 2: Costco's JavaScript SDK runs:
        anonymous_id = generate_random_uuid() → "anon_abc123xyz"
Step 3: Stores "anon_abc123xyz" in a FIRST-PARTY cookie (costco.com domain)
Step 4: ALL events from this session tagged with "anon_abc123xyz"

Next week, John visits AGAIN (same browser, same cookie, not logged in):
  → Browser still has the "anon_abc123xyz" cookie
  → All events again tagged with "anon_abc123xyz"
  → System knows: SAME browser/device visited twice
  → System does NOT know: this is "John Smith" specifically

Then John LOGS IN:
  → Login event: {anonymous_id: "anon_abc123xyz", member_id: "M001234"}
  → EUREKA! anon_abc123xyz = M001234 = John Smith
  → All prior anonymous sessions now linked to John Smith

THE "IDENTITY STITCH" = The login event that links anonymous → known.

ANONYMOUS ID    ──── login event ────►    MEMBER ID
"anon_abc123"                             "M001234"
(unknown device)                          (John Smith, known)
```

---

# CHAPTER 2: THE IDENTITY GRAPH

## 2.1 What is an Identity Graph?

```
AN IDENTITY GRAPH is a database that maps ALL identifiers for the SAME person
into one unified profile.

JOHN SMITH'S IDENTITY GRAPH NODE:

┌─────────────────────────────────────────────────────────────────────┐
│                    JOHN SMITH — Canonical Entity                     │
│                                                                      │
│  DETERMINISTIC LINKS (certain, 100% confidence):                    │
│  ├── member_id     = "M001234"                     ← canonical ID   │
│  ├── email_hash    = SHA256("john.smith@gmail.com")                  │
│  └── phone_hash    = SHA256("+1-555-0123")                          │
│                                                                      │
│  STITCHED LINKS (confirmed via login event, 100%):                  │
│  ├── anonymous_id  = "anon_abc123"  (MacBook/Chrome)                │
│  └── anonymous_id  = "anon_def456"  (iPhone/Safari)                 │
│  └── idfa          = "A1B2C3..."    (Costco iOS app)                │
│                                                                      │
│  PROBABILISTIC LINKS (inferred from signals, <100%):                │
│  └── anonymous_id  = "anon_ghi789"  (iPad/Firefox, 82% confidence)  │
│                                                                      │
│  METADATA:                                                           │
│  first_seen: 2023-06-01 | last_seen: 2024-01-15                     │
│  link_count: 5 devices  | average_confidence: 0.96                  │
└─────────────────────────────────────────────────────────────────────┘

KEY TERMS:
  CANONICAL ENTITY:  The "true" person record (member_id is the canonical ID)
  IDENTITY STITCH:   The act of linking anonymous_id → member_id via login
  CONFIDENCE SCORE:  How certain we are two IDs belong to the same person
```

## 2.2 How the Identity Graph Builds Over Time

```
DAY 1: First visit (anonymous, MacBook/Chrome)
  Event: {anonymous_id:"anon_abc", event_type:"page_view"}
  Graph: [anon_abc] → (unknown person)

DAY 3: Second visit, same browser
  Event: {anonymous_id:"anon_abc", event_type:"click", campaign:"camp_001"}
  Graph: [anon_abc] → (unknown person, 2 visits)

DAY 5: New visit on iPhone (different device, also anonymous)
  Event: {anonymous_id:"anon_def", event_type:"page_view", device:"mobile"}
  Graph: [anon_abc] → (person A — unknown)
         [anon_def] → (person B — unknown, same IP as A → maybe same house?)

DAY 7: John LOGS IN on iPhone ← THE STITCH MOMENT
  Event: {anonymous_id:"anon_def", member_id:"M001234", event_type:"login"}

  ══════════════ IDENTITY STITCH FIRES ══════════════
  Graph NOW:
  M001234 ←────────────── anon_def  (CERTAIN — login event)
  
  M001234 = John Smith. We now know anon_def is John's iPhone.

DAY 7 (continued): Still logged in, browsing on iPhone
  Events: {anonymous_id:"anon_def", member_id:"M001234", event_type:"product_view"}
  (Both IDs in same event = logged-in session)

DAY 10: MacBook visit (Chrome, NOT logged in)
  Event: {anonymous_id:"anon_abc", ip_hash:"same_ip_as_M001234"}
  
  PROBABILISTIC LINK ATTEMPT:
  Check: does M001234 use this IP? YES (matched in graph).
  Check: does fingerprint match? YES (same browser fingerprint).
  Confidence: 85% → PROBABILISTIC link created.
  
  Graph NOW:
  M001234 ←──────────────── anon_def  (100% certain)
           ←── (prob, 85%) ─ anon_abc  (probably same person)

DAY 12: John logs in on MacBook ← SECOND STITCH
  Event: {anonymous_id:"anon_abc", member_id:"M001234", event_type:"login"}
  
  ANOTHER STITCH FIRES!
  Graph NOW:
  M001234 ←──────────────── anon_def  (100% certain)
          ←──────────────── anon_abc  (NOW 100% — upgraded from 85%)
  
  BONUS: All prior anonymous events from anon_abc (3 weeks of browsing)
         are NOW attributed to M001234.
         The 8 AM click on Day 1? That's John's too. Attribution corrected.
```

---

# CHAPTER 3: IDENTITY RESOLUTION ARCHITECTURE ON GCP

## 3.1 Complete System — All Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│              IDENTITY RESOLUTION PLATFORM — COMPLETE ARCHITECTURE       │
└─────────────────────────────────────────────────────────────────────────┘

LAYER 1: DATA COLLECTION — generating identity signals
───────────────────────────────────────────────────────
┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Web Browser    │  │  Mobile App      │  │  Server-Side     │
│  (JS SDK)       │  │  (iOS/Android)   │  │  (backend)       │
│                 │  │                  │  │                  │
│ Every page:     │  │ Every app open:  │  │ On login/        │
│ ─ create/read   │  │ ─ read device_id │  │   purchase:      │
│   anonymous_id  │  │   (IDFA/GAID)    │  │ ─ member_id known│
│ ─ read          │  │ ─ read anon_id   │  │ ─ email known    │
│   member_id if  │  │ ─ send event     │  │ ─ both IDs in    │
│   logged in     │  │                  │  │   same event     │
│ ─ send event    │  │                  │  │                  │
└────────┬────────┘  └────────┬─────────┘  └────────┬─────────┘
         └───────────────────┴────────────────────────┘
                              │
                              ▼
LAYER 2: INGESTION
──────────────────
                    Cloud Run API Gateway
                    (validates, enriches with server timestamp)
                              │
                              ▼
                    Cloud Pub/Sub "identity-events"
                    (durable buffer, 7-day retention)
                              │
                              ▼
LAYER 3: IDENTITY PROCESSING (the core engine)
────────────────────────────────────────────────
                    Cloud Dataflow Streaming Job
                    
                    Watches for two types of events:
                    
                    TYPE A — STITCH EVENT (login):
                    {anonymous_id: "anon_abc", member_id: "M001234"}
                    → DETERMINISTIC STITCH: anon_abc = M001234 (100%)
                    → Writes to identity graph immediately
                    → Updates Firestore for real-time serving
                    → Triggers retroactive attribution job
                    
                    TYPE B — ANONYMOUS SIGNAL:
                    {anonymous_id: "anon_xyz", ip: "...", fingerprint: "..."}
                    → Check: does any member share this IP/fingerprint?
                    → If yes: PROBABILISTIC LINK (score = 0.78)
                    → Only write if confidence >= 0.70
                              │
                              ▼
LAYER 4: IDENTITY STORE
────────────────────────
  BigQuery (analytics)          Cloud Firestore (real-time)
  identity.identity_graph       identity_graph collection
  ─────────────────────         ────────────────────────────
  Full history of all links     Key-value: anon_id → member_id
  Complex queries (batch)       Sub-5ms lookups (real-time)
  Attribution analysis          Ad serving personalization
  Audience building             Session identification
                              │
                              ▼
LAYER 5: USE CASES
──────────────────
  Ad Targeting         Attribution            Personalization
  ─────────────        ────────────           ───────────────
  Suppress ad after    8AM click on           Logged-out user
  purchase across      iPhone → 9PM           sees personalized
  ALL devices          MacBook purchase       content based on
  not just one         correctly              their member profile
```

## 3.2 Database Tables

```sql
-- TABLE 1: RAW IDENTITY EVENTS
-- Every event that has any identity signal goes here.
-- The INPUT to the identity resolution engine.

CREATE TABLE `project.identity.identity_events`
(
    event_id            STRING    NOT NULL,
    event_type          STRING    NOT NULL,  -- 'login','page_view','app_open','purchase'
    event_timestamp     TIMESTAMP NOT NULL,
    
    -- ANONYMOUS IDs (what we see without login)
    anonymous_id        STRING,   -- first-party cookie ID
    device_fingerprint  STRING,   -- browser fingerprint hash
    idfa                STRING,   -- iOS advertising ID (if consented)
    gaid                STRING,   -- Android advertising ID
    ip_address_hash     STRING,   -- SHA256(ip) — hashed for privacy
    
    -- AUTHENTICATED IDs (what we see after login)
    member_id           STRING,   -- YOUR canonical user ID
    email_hash          STRING,   -- SHA256(lowercase(trim(email)))
    phone_hash          STRING,   -- SHA256(phone)
    
    -- CONTEXT
    device_type         STRING,   -- 'mobile', 'desktop', 'tablet', 'tv'
    browser             STRING,
    os                  STRING,
    
    -- IS THIS A STITCH EVENT?
    -- True when BOTH anonymous_id AND member_id are present
    is_identity_stitch  BOOL      DEFAULT FALSE
)
PARTITION BY DATE(event_timestamp)
CLUSTER BY member_id, anonymous_id;

-- ─────────────────────────────────────────────────────────────────────

-- TABLE 2: THE IDENTITY GRAPH
-- The OUTPUT of identity resolution.
-- One row per (canonical_id, identifier) pair.
-- THIS IS WHAT YOU QUERY.

CREATE TABLE `project.identity.identity_graph`
(
    canonical_id        STRING    NOT NULL,  -- member_id (the authoritative ID)
    identifier          STRING    NOT NULL,  -- any other ID linked to this member
    identifier_type     STRING    NOT NULL,  -- 'cookie','idfa','email_hash','fingerprint'
    
    -- HOW CERTAIN ARE WE?
    link_type           STRING    NOT NULL,  -- 'deterministic' or 'probabilistic'
    confidence_score    FLOAT64   NOT NULL,  -- 1.0=certain, 0.85=85% likely
    link_source         STRING,              -- 'login_event','ip_match','fingerprint_match'
    
    -- WHEN?
    first_seen_at       TIMESTAMP NOT NULL,
    last_seen_at        TIMESTAMP NOT NULL,
    link_established_at TIMESTAMP NOT NULL,
    
    -- DEVICE CONTEXT
    device_type         STRING,
    browser             STRING,
    os                  STRING
)
CLUSTER BY canonical_id, identifier;

-- ─────────────────────────────────────────────────────────────────────

-- HOW TO USE THESE TABLES:

-- Q1: "Who is this anonymous visitor?"
SELECT canonical_id, confidence_score, link_type, device_type
FROM `project.identity.identity_graph`
WHERE identifier = 'anon_abc123'
ORDER BY confidence_score DESC
LIMIT 1;
-- Answer: M001234, confidence=1.0, link_type='deterministic'

-- Q2: "What devices does M001234 use?"
SELECT identifier, identifier_type, confidence_score, device_type, last_seen_at
FROM `project.identity.identity_graph`
WHERE canonical_id = 'M001234'
ORDER BY last_seen_at DESC;
-- Answer: anon_abc (MacBook/Chrome, 1.0), anon_def (iPhone/Safari, 1.0),
--         A1B2C3 (IDFA, 1.0), anon_ghi (iPad, 0.82)

-- Q3: "Find all attribution touchpoints for M001234's last purchase"
SELECT e.event_type, e.event_timestamp, e.campaign_id, e.anonymous_id, e.device_type
FROM `project.raw.ad_events` e
WHERE e.anonymous_id IN (
    SELECT identifier FROM `project.identity.identity_graph`
    WHERE canonical_id = 'M001234'
)
AND e.event_timestamp >= TIMESTAMP_SUB(
    (SELECT MIN(event_timestamp) FROM `project.raw.ad_events`
     WHERE event_type = 'purchase' AND member_id = 'M001234'),
    INTERVAL 30 DAY
)
ORDER BY event_timestamp;
-- Shows: ALL clicks/impressions from ALL devices in 30 days before purchase
```

## 3.3 The Dataflow Identity Pipeline

```python
# KEY LOGIC: The Identity Stitch Handler
# This fires when BOTH anonymous_id AND member_id appear in same event

import apache_beam as beam
import json
from datetime import datetime

class DetectAndProcessStitch(beam.DoFn):
    """
    The core identity resolution logic.
    
    Processes every incoming event and detects identity signals:
    - Stitch events (login): anonymous_id + member_id together → certain link
    - Anonymous signals: anonymous_id only → store for probabilistic matching
    """
    
    def process(self, element):
        event = json.loads(element.decode('utf-8'))
        
        anon_id   = event.get('anonymous_id')
        member_id = event.get('member_id')
        timestamp = event.get('event_timestamp')
        
        # ─── CASE 1: DETERMINISTIC STITCH (login moment) ───────────────
        # Both IDs present = user just authenticated
        
        if anon_id and member_id:
            
            # Link the cookie to the member (100% certain)
            yield {
                'action':           'write_to_graph',
                'canonical_id':     member_id,
                'identifier':       anon_id,
                'identifier_type':  'cookie',
                'link_type':        'deterministic',
                'confidence_score': 1.0,
                'link_source':      'login_event',
                'timestamp':        timestamp,
                'device_type':      event.get('device_type')
            }
            
            # Also link IDFA if present (same login event proves it's the same person)
            if event.get('idfa'):
                yield {
                    'action':           'write_to_graph',
                    'canonical_id':     member_id,
                    'identifier':       event['idfa'],
                    'identifier_type':  'idfa',
                    'link_type':        'deterministic',
                    'confidence_score': 1.0,
                    'link_source':      'login_event',
                    'timestamp':        timestamp
                }
            
            # Trigger retroactive attribution
            # All prior events from this anon_id → now attributed to member_id
            yield beam.pvalue.TaggedOutput('retroactive', {
                'anonymous_id': anon_id,
                'member_id':    member_id,
                'as_of':        timestamp
            })
        
        # ─── CASE 2: ANONYMOUS SIGNAL (no login, just browsing) ─────────
        # Store signals for probabilistic matching
        
        elif anon_id and not member_id:
            yield beam.pvalue.TaggedOutput('anonymous_signal', {
                'anonymous_id':     anon_id,
                'ip_hash':          event.get('ip_address_hash'),
                'fingerprint':      event.get('device_fingerprint'),
                'device_type':      event.get('device_type'),
                'timestamp':        timestamp
            })


class ProbabilisticMatcher(beam.DoFn):
    """
    For anonymous signals: attempt to match to a known member.
    Uses IP address and browser fingerprint as signals.
    Only creates a link if confidence >= 0.70.
    """
    
    def process(self, element, known_members_by_ip, known_members_by_fp):
        """
        known_members_by_ip: dict {ip_hash: [member_ids]} (loaded as side input)
        known_members_by_fp: dict {fingerprint: [member_ids]} (loaded as side input)
        """
        anon_id     = element.get('anonymous_id')
        ip_hash     = element.get('ip_hash')
        fingerprint = element.get('fingerprint')
        
        best_match = None
        best_confidence = 0.0
        
        # Check IP match
        if ip_hash and ip_hash in known_members_by_ip:
            candidates = known_members_by_ip[ip_hash]
            if len(candidates) == 1:  # single member at this IP = higher confidence
                confidence = 0.70
                if candidates[0] not in (best_match,):
                    best_match = candidates[0]
                    best_confidence = confidence
        
        # Check fingerprint match (stronger signal — exact browser match)
        if fingerprint and fingerprint in known_members_by_fp:
            candidates = known_members_by_fp[fingerprint]
            if len(candidates) == 1:
                confidence = 0.88  # fingerprint is more unique than IP
                if confidence > best_confidence:
                    best_match = candidates[0]
                    best_confidence = confidence
        
        # Combined IP + fingerprint = even higher confidence
        # (Two independent signals pointing to same person)
        
        # Only emit if confidence meets threshold
        if best_match and best_confidence >= 0.70:
            yield {
                'action':           'write_to_graph',
                'canonical_id':     best_match,
                'identifier':       anon_id,
                'identifier_type':  'cookie',
                'link_type':        'probabilistic',
                'confidence_score': best_confidence,
                'link_source':      'ip_fingerprint_match',
                'timestamp':        element.get('timestamp')
            }
```

---

# CHAPTER 4: HOW IDENTITY IS USED FOR AD TARGETING

## 4.1 Building a Retargeting Audience

```sql
-- BUSINESS RULE: Target people who viewed the membership page in last 30 days
--               but have NOT yet purchased a membership.

-- STEP 1: Find ALL anonymous IDs that viewed the membership page
WITH viewed_membership AS (
    SELECT DISTINCT anonymous_id
    FROM `project.raw.ad_events`
    WHERE event_type   = 'page_view'
      AND page_url     LIKE '%/membership%'
      AND event_date  >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
),

-- STEP 2: Find anonymous IDs that we KNOW belong to existing members
-- (Don't retarget people who already bought — waste of money!)
already_members AS (
    SELECT DISTINCT ig.identifier AS anonymous_id
    FROM `project.identity.identity_graph` ig
    JOIN `project.marts.dim_members` m ON ig.canonical_id = m.member_id
    WHERE ig.identifier_type  = 'cookie'
      AND ig.confidence_score >= 0.90  -- high confidence only
      AND m.membership_status = 'active'  -- they ARE a member
),

-- STEP 3: PROSPECTS = viewed page BUT not yet a member
prospects AS (
    SELECT vm.anonymous_id
    FROM viewed_membership vm
    LEFT JOIN already_members am USING (anonymous_id)
    WHERE am.anonymous_id IS NULL  -- exclude existing members
),

-- STEP 4: Try to resolve prospects to emails for Customer Match
-- (anonymous users who we later stitched to their email)
prospects_with_email AS (
    SELECT
        p.anonymous_id,
        ig.canonical_id AS member_id,
        m.email_hash
    FROM prospects p
    JOIN `project.identity.identity_graph` ig
        ON p.anonymous_id = ig.identifier
        AND ig.confidence_score >= 0.90
    JOIN `project.marts.dim_members` m ON ig.canonical_id = m.member_id
    WHERE m.email_marketing_opt_in = TRUE   -- GDPR: only opted-in users
)

-- These email hashes are uploaded to Google/Meta Customer Match
SELECT email_hash, COUNT(*) AS prospects_matched
FROM prospects_with_email
GROUP BY email_hash;

-- Upload to Google Ads Customer Match API
-- → Google checks if any logged-in Google user has this email
-- → If yes: show them your membership ad across Google, YouTube, Gmail
-- → Even if they're NOT on costco.com right now
```

## 4.2 Customer Match — The Bridge to Ad Platforms

```
THE PROBLEM:
  Your identity graph knows: anon_abc = M001234 = john.smith@gmail.com
  But Google/Meta/TikTok don't have access to your identity graph.
  When John visits cnn.com, how do Google show him YOUR ad?

THE SOLUTION: CUSTOMER MATCH

You upload a list of email hashes to Google Ads.
Google checks: "Is any of our 3 billion logged-in users' email a match?"
John is logged into Gmail → Google matches → shows him your ad.

FLOW:
  BigQuery audience query
      │ export email_hashes
      ▼
  Python script
      │ upload to Google Ads API
      ▼
  Google Ads Customer List: "Costco Membership Prospects"
      │ campaign targets this list
      ▼
  John opens YouTube (logged in as john.smith@gmail.com)
  → Google: "his email hash matches Costco's list"
  → Shows Costco membership ad

PRIVACY:
  You NEVER send raw emails to Google/Meta.
  You ONLY send: SHA256(lowercase(trim(email)))
  Google hashes THEIR users' emails the same way.
  They compare hashes. If equal → same person.
  No raw email ever leaves your system.
  
  Meta calls it: "Custom Audiences"
  TikTok calls it: "Customer File Audiences"
  They all accept the same SHA256 hash format.

PYTHON IMPLEMENTATION:
```

```python
from google.ads.googleads.client import GoogleAdsClient
import hashlib

def upload_customer_match_list(email_hashes: list, list_name: str):
    """
    Upload hashed emails to Google Ads Customer Match.
    Used for targeting: show ads to these specific users across Google properties.
    """
    client = GoogleAdsClient.load_from_dict({...})  # your Google Ads credentials
    
    user_data_service = client.get_service("UserDataService")
    customer_id = "YOUR_GOOGLE_ADS_CUSTOMER_ID"
    
    # Create user identifiers from email hashes
    user_identifiers = []
    for email_hash in email_hashes:
        user_id = client.get_type("UserIdentifier")
        user_id.hashed_email = email_hash  # already SHA256 hashed
        user_identifiers.append(user_id)
    
    # Upload in batches of 10,000 (Google's limit per request)
    batch_size = 10000
    for i in range(0, len(user_identifiers), batch_size):
        batch = user_identifiers[i:i + batch_size]
        
        request = client.get_type("UploadUserDataRequest")
        request.customer_id = customer_id
        
        for uid in batch:
            operation = client.get_type("UserDataOperation")
            operation.create.user_identifiers.append(uid)
            request.operations.append(operation)
        
        response = user_data_service.upload_user_data(request=request)
        print(f"Uploaded batch {i//batch_size + 1}: {len(batch)} users")
    
    print(f"Total uploaded: {len(email_hashes)} users to '{list_name}'")

# Build audience from BigQuery and upload
def run_audience_export():
    from google.cloud import bigquery
    
    bq = bigquery.Client()
    
    # Query prospects from BigQuery
    results = bq.query("""
        SELECT DISTINCT email_hash
        FROM `project.identity.prospects_with_email`
        WHERE DATE(_exported_at) = CURRENT_DATE()
    """).result()
    
    email_hashes = [row.email_hash for row in results]
    
    print(f"Found {len(email_hashes)} prospects to upload")
    upload_customer_match_list(email_hashes, "Membership Prospects - Last 30 Days")
```

---

## 4.3 Real-Time Identity Lookup for Ad Serving

```
THE PERFORMANCE CHALLENGE:
  Identity graph in BigQuery: 500M rows.
  BigQuery query time: 1-3 seconds.
  Ad serving decision must be made in: < 50 milliseconds.
  
  BigQuery is too slow for real-time ad serving.
  
SOLUTION: TWO-TIER STORAGE

┌────────────────────────────────────────────────────────────────────────┐
│  TIER 1: CLOUD FIRESTORE (real-time cache)                             │
│  ─────────────────────────────────────────────────────────────────────│
│  Purpose:    Sub-5ms identity lookups for real-time ad serving        │
│  Storage:    Key-value: anonymous_id → {member_id, confidence, tier}  │
│  What's in:  High-confidence links only (≥ 0.90)                      │
│  Updates:    Real-time via Dataflow whenever a new stitch is detected  │
│  Latency:    < 5 milliseconds                                          │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│  TIER 2: BIGQUERY (analytics store)                                    │
│  ─────────────────────────────────────────────────────────────────────│
│  Purpose:    Full history, complex queries, attribution analysis       │
│  Storage:    All links including probabilistic, full history           │
│  What's in:  Everything                                                │
│  Updates:    Near-real-time via Dataflow streaming inserts             │
│  Latency:    1-3 seconds (acceptable for batch/analytics use)         │
└────────────────────────────────────────────────────────────────────────┘
```

```python
import google.cloud.firestore as firestore

class IdentityLookupService:
    """Real-time identity resolution for ad serving. < 5ms latency."""
    
    def __init__(self, project_id: str):
        self.db = firestore.Client(project=project_id)
    
    def resolve_anonymous_id(self, anonymous_id: str) -> dict:
        """
        Look up: "Who is this anonymous visitor?"
        
        Called on EVERY page load where we serve ads.
        Must return in < 5ms.
        """
        doc = self.db.collection('identity').document(anonymous_id).get()
        
        if not doc.exists:
            # Unknown visitor — no link exists
            return {
                'is_known':     False,
                'member_id':    None,
                'confidence':   0.0,
                'member_tier':  'unknown',
                'segments':     ['prospecting']
            }
        
        data = doc.to_dict()
        member_id = data.get('canonical_id')
        
        if not member_id:
            return {'is_known': False, 'confidence': data.get('confidence', 0)}
        
        # Load member profile (also in Firestore for speed)
        profile_doc = self.db.collection('member_profiles').document(member_id).get()
        profile = profile_doc.to_dict() if profile_doc.exists else {}
        
        return {
            'is_known':         True,
            'member_id':        member_id,
            'confidence':       data.get('confidence', 1.0),
            'link_type':        data.get('link_type', 'deterministic'),
            'member_tier':      profile.get('tier', 'standard'),
            'days_since_login': profile.get('days_since_last_activity', 999),
            'recent_categories':profile.get('recent_browse_categories', []),
            'is_expiring_soon': profile.get('membership_expiring_soon', False),
            'segments':         profile.get('ad_segments', ['general'])
        }
    
    def record_new_stitch(self, anonymous_id: str, member_id: str, confidence: float = 1.0):
        """Write new identity link to Firestore immediately (real-time)."""
        self.db.collection('identity').document(anonymous_id).set({
            'canonical_id': member_id,
            'confidence':   confidence,
            'link_type':    'deterministic' if confidence == 1.0 else 'probabilistic',
            'linked_at':    firestore.SERVER_TIMESTAMP
        }, merge=True)


# HOW IT'S USED IN THE AD SERVING FLOW:

identity_service = IdentityLookupService('costco-martech')

def decide_which_ad_to_show(request) -> str:
    """
    Called when a user loads a page with an ad slot.
    Must return the right campaign in < 50ms total.
    """
    anon_id = request.cookies.get('anon_id', 'unknown_visitor')
    
    # Step 1: Resolve identity (< 5ms via Firestore)
    identity = identity_service.resolve_anonymous_id(anon_id)
    
    # Step 2: Make personalized ad decision
    if identity['is_known']:
        tier       = identity['member_tier']
        categories = identity['recent_categories']
        inactive   = identity['days_since_login'] > 60
        expiring   = identity['is_expiring_soon']
        
        # Personalized campaign selection:
        if expiring:
            return 'membership_renewal_urgent'
        elif inactive and tier in ('gold', 'executive'):
            return f'winback_{tier}_member'
        elif 'tv' in categories or 'electronics' in categories:
            return 'electronics_member_deal'
        else:
            return 'general_member_engagement'
    
    else:
        # Unknown visitor → prospecting
        device = request.headers.get('User-Agent', '')
        if 'iPhone' in device or 'Android' in device:
            return 'mobile_prospecting'
        else:
            return 'desktop_prospecting'
```

---

# CHAPTER 5: THE THREE TARGETING SCENARIOS

## Scenario A: User is Logged In (Easiest)

```
John opens Costco app on iPhone. He's logged in.
anonymous_id = "anon_def" | member_id = "M001234" (both present)

WHAT YOU KNOW:
  Member ID:           M001234 = John Smith
  Loyalty tier:        Gold member
  Membership expiry:   6 months away
  Last purchase:       60 days ago (electronics)
  Recent browsing:     TVs, headphones
  Has executive tier?  No

AD DECISION (in < 50ms):
  "He's been inactive 60 days AND browsed electronics"
  → Show: "Gold members save $300 on 75-inch TVs this week"
  
  "He's Gold but not Executive"
  → Also eligible: "Upgrade to Executive, save $100/year"
  
  NOT appropriate: "Become a Costco member" (he already is one!)
  NOT appropriate: Membership acquisition ads (waste of budget)

HOW AD IS DELIVERED:
  Firestore lookup: anon_def → M001234 (< 5ms)
  Profile lookup: M001234 → {tier:gold, last_purchase:60d, browsed:tv} (< 5ms)
  Ad decision: electronics_retargeting campaign (1ms)
  Total: < 11ms
```

## Scenario B: Anonymous But Previously Stitched

```
John opens Chrome on MacBook. NOT logged in.
anonymous_id = "anon_abc" | member_id = NOT in session

WHAT SYSTEM SEES:
  An "anonymous" visitor with anon_abc

WHAT IDENTITY GRAPH KNOWS:
  anon_abc → M001234 (confidence: 1.0, stitched when John logged in 2 days ago)

LOOKUP RESULT (< 5ms via Firestore):
  {is_known: True, member_id: M001234, confidence: 1.0, tier: 'gold', ...}

EFFECT:
  John is ANONYMOUS to his browser session.
  But YOUR SYSTEM knows exactly who he is.
  
  You serve him a PERSONALIZED experience even though he's "not logged in":
  ✓ Show member pricing without requiring login
  ✓ Show "welcome back" content (not "become a member" ads)
  ✓ Show electronics retargeting (based on his profile)
  ✓ Track this session in his full journey for attribution
  ✗ DON'T show him membership acquisition ads (he has a membership!)

THIS IS THE POWER OF THE IDENTITY GRAPH.
You know who he is. He doesn't know you know.
(Within GDPR/consent framework, of course.)
```

## Scenario C: Brand New Unknown Visitor

```
Brand new visitor. Never been to costco.com. No cookie.
anonymous_id = "anon_new_xyz" (just generated)
member_id = NONE
Identity graph lookup = EMPTY (no link found)

WHAT YOU KNOW: Almost nothing.
  Device: mobile
  Browser: Chrome/Android
  Location: San Francisco (approximate, from IP)
  Time: 7 PM
  Source: clicked a Google Search ad for "warehouse membership"
  Referrer: google.com/search

WHAT YOU CAN DO: Lookalike / Behavioral Targeting

The visitor's SIGNALS suggest they look like your best prospects:
  - Mobile user in SF
  - Came from search (high intent!)
  - Searched "warehouse membership" (VERY high intent)
  - Evening browsing time
  
  Compare to your KNOWN member profiles:
  "People who searched 'warehouse membership' and converted:
   → 68% were mobile users
   → 72% came from Google Search
   → Typical conversion happens within 24 hours of first visit"
  
  Assign: prospect_score = 0.85 (looks highly likely to convert)
  
  Show: Standard membership acquisition campaign.
  
  Don't show: Executive membership (not a member yet).
  Don't show: Electronics deals (no purchase history).
  
  Track: Store anon_new_xyz with this session's signals.
  If they later register → STITCH → retroactively attribute this visit.
```

---

# CHAPTER 6: PRIVACY AND THE FUTURE

## 6.1 GDPR/CCPA Constraints

```
YOU MUST GET CONSENT before:
  ✗ Setting advertising cookies (beyond technically necessary)
  ✗ Building behavioral profiles
  ✗ Cross-device tracking
  ✗ Sharing data with ad platforms

THE CONSENT BANNER (that annoying popup):
  "Accept All" → you can track them fully
  "Reject All" → you CANNOT build identity graph for them
               → CANNOT set advertising cookies
               → CANNOT retarget them on Google/Meta
  
  For GDPR: "Reject All" must be as easy to click as "Accept All"
  
WHAT YOU CAN DO WITHOUT CONSENT:
  ✓ Session cookie (shopping cart, login state)
  ✓ First-party analytics (your own site, aggregated)
  ✓ Server-side conversion data (your own records of purchases)

PII HANDLING RULES:
  Never store raw email in event tables
  Never send raw email to ad platforms
  Always: SHA256(lowercase(trim(email)))
  
RIGHT TO ERASURE (30-day deadline):
  Delete from identity_graph (all their anonymous IDs)
  Delete from member profiles
  Delete from all event tables
  Remove from Google/Meta Customer Match lists
```

## 6.2 The Future — What's Replacing Cookies

```
WHAT'S DYING:
  Third-party cookies:  Chrome deprecating 2024-2025
  IDFA:                 80% opt-out after Apple ATT
  IP tracking:          Privacy laws restricting

WHAT'S REPLACING IT:

1. FIRST-PARTY DATA (most important)
   "Every logged-in user is worth 100x an anonymous cookie."
   Strategy: Give users REASONS to log in.
     → Save cart (requires login)
     → Member pricing (requires login)
     → Loyalty points (requires login)
   More logged-in sessions = more deterministic identity = better targeting.
   This is why Costco's membership model is a COMPETITIVE ADVANTAGE.

2. SERVER-SIDE TRACKING
   Instead of: browser fires pixel to Google/Meta
   New model:  YOUR server sends conversion data to Google/Meta via API
   
   Called: "Conversions API" (Meta), "Enhanced Conversions" (Google)
   
   You send: {event: "purchase", email_hash: sha256(email), value: 49.99}
   Platform matches to their user → attributes the conversion
   
   Benefits: Not blocked by ad blockers, works without third-party cookies

3. CLEAN ROOMS
   Costco and Meta want to measure ad effectiveness together.
   Neither can share raw user data (GDPR).
   
   Clean Room = secure environment where:
   → Costco brings purchase data
   → Meta brings ad impression data
   → System computes: "X% of people who saw your Meta ad bought at Costco"
   → NEITHER side sees the other's raw data
   
   Examples: Meta Advanced Analytics, Google Ads Data Hub, Snowflake Clean Room

4. COHORT-BASED TARGETING
   Instead of: target user X individually
   New model:  target Cohort 7 = "users who recently browsed electronics"
   
   Individual users anonymous within the cohort.
   Less precise but privacy-preserving.
   Google's Privacy Sandbox / Topics API works this way.
```

---

# CHAPTER 7: THE COMPLETE INTERVIEW ANSWER

## The 4-Minute System Design Answer

**Frame the problem** (30 seconds):
*"Identity resolution is the process of connecting a user's behavior across all their devices and sessions — logged in or not — into a single unified profile. The core challenge is that users are often anonymous. The solution is building an identity graph that links anonymous identifiers to known member IDs."*

**The two identifier types** (45 seconds):
*"There are two types of identifiers. Deterministic ones — member ID, hashed email, hashed phone — are 100% certain because the user authenticated. They're only available during logged-in sessions, maybe 20-40% of traffic. Probabilistic ones — IP address, browser fingerprint, mobile device ID — are educated guesses based on signals, 70-95% confident. The identity graph combines both."*

**Anonymous ID and the stitch** (1 minute):
*"On first visit, the SDK generates a random anonymous ID stored as a first-party cookie. Every event from that browser is tagged with it. The key moment is the 'identity stitch' — when a user logs in, you receive both the anonymous ID and the member ID in the same event. You link them in the identity graph with 100% confidence. Going forward, even when that person browses without logging in, you look up their anonymous ID in the graph and you know who they are."*

**The architecture** (1 minute):
*"On GCP: events flow to Pub/Sub, a Dataflow streaming pipeline watches for stitch events and writes to two stores: BigQuery for full history and analytics, and Firestore for sub-5-millisecond real-time lookups during ad serving. When a user visits, the ad server calls Firestore with the anonymous ID and gets back the member profile in under 5ms — fast enough for real-time personalization."*

**How it enables targeting** (45 seconds):
*"This powers three capabilities. One: cross-device consistency — if John buys a membership on his laptop, we stop showing him membership ads on his phone. Two: proper attribution — we can trace a purchase back to the ad click that happened 20 minutes earlier on a different device. Three: Customer Match — we export hashed emails to Google and Meta, who match them to their logged-in users and show our ads across their platforms, even when users aren't on our site."*

**Privacy** (30 seconds):
*"Everything is governed by GDPR. We only build identity graphs for users who consented to tracking. PII is always SHA256 hashed before sharing with platforms. Users can request erasure within 30 days. And as third-party cookies die, the system shifts to first-party login data and server-side conversion APIs — which is why encouraging users to log in is now the #1 strategic priority in identity management."*

---

# SUMMARY: ONE-PAGE REFERENCE

```
IDENTITY RESOLUTION — COMPLETE CHEAT SHEET

IDENTIFIERS:
  Deterministic (100% certain):   member_id, email_hash, phone_hash
  Probabilistic (best guess):     IP address, browser fingerprint, IDFA/GAID
  Device-level:                   first-party cookie → anonymous_id

THE ANONYMOUS ID:
  Generated by SDK on first visit → stored in first-party cookie
  Persists across sessions (same browser = same anonymous_id)
  Identifies a DEVICE, not a PERSON (until stitched)

THE IDENTITY STITCH:
  Trigger: login event with BOTH anonymous_id AND member_id
  Result: permanent link in identity graph (100% confidence)
  Bonus: retroactively attributes all prior anonymous sessions to this member

THE IDENTITY GRAPH:
  Maps: anonymous_id ↔ member_id (many-to-one)
  Includes: link type, confidence score, when linked, device context
  BigQuery: full analytics (1-3 sec queries)
  Firestore: real-time serving (< 5ms lookups)

THREE TARGETING SCENARIOS:
  1. Logged in:          member_id known → full personalization
  2. Anonymous+stitched: anon_id → graph → member profile → personalization
  3. Truly unknown:      behavioral signals → lookalike/prospecting targeting

CUSTOMER MATCH:
  Export: SHA256(email) list from BigQuery
  Upload: to Google/Meta via API
  Effect: your ad shows to matched users anywhere on that platform
  Privacy: no raw email ever shared — only hashes

PRIVACY:
  Consent required for tracking (cookie banner)
  SHA256 hash all PII before sharing with ad platforms
  30-day deletion obligation on erasure requests
  First-party data > third-party cookies (third-party cookies dying)

THE FUTURE:
  Less: third-party cookies, IDFA
  More: first-party login data, server-side APIs, clean rooms, cohort targeting
  Strategic implication: encourage login at EVERY touchpoint
```
