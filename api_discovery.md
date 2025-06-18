# Gong API Discovery Documentation

**Generated from HAR Analysis**: `gong-multitab-capture.har`  
**Total HAR Entries**: 3,091  
**Gong API Calls**: 915  
**Unique Endpoint Patterns**: 232  
**Analysis Date**: 2025-06-16

## 🎯 **Core Authentication & Session Management**

### Authentication Flow
- **SAML Login**: `POST https://app.gong.io/welcome/okta/saml/login`
- **Session Token**: `GET https://us-14496.app.gong.io/ajax/common/rtkn` (34 calls)
- **Key Store Access**: `GET https://us-14496.app.gong.io/ajax/common/ksa` (18 calls)

## 📊 **Primary API Categories**

### 1. **Home & Dashboard APIs**
```
GET /ajax/home/calls/my-calls
GET /ajax/home/calls/listen-later-counter
GET /ajax/home/inbox/
GET /userjourneywebapi/ajax/home/forecast/init
GET /userjourneywebapi/ajax/home/recommendations
GET /userjourneywebapi/ajax/home/announcements
GET /userjourneywebapi/ajax/home/deals/is-entitled
GET /userjourneywebapi/ajax/home/initiatives/is-entitled
GET /userjourneywebapi/ajax/home/ask-anything/is-entitled
```

### 2. **Account & Contact Management**
```
GET /account
GET /ajax/account
GET /ajax/account/opportunities
GET /ajax/account/people
GET /ajax/account/day-activities
GET /ajax/account/email-expanded
GET /ajax/account/meeting-expanded
GET /ajax/account/call-expanded
GET /ajax/contacts/get-single-contact-details
GET /ajax/contacts/get-engagements
GET /ajax/contacts/crm/configured-fields-labels
GET /ajax/contacts/crm/managed-fields
GET /ajax/contacts/crm/configured-fields-data
POST /ajax/contacts/get-board-contacts
```

### 3. **Call & Recording Management**
```
GET /call
GET /call/detailed-transcript
GET /call/share-modal/non-processed-call-data
GET /json/call/call-recording-status
GET /json/call/get-potential-internal-shares
GET /json/call/get-potential-external-shares
GET /json/call/get-current-external-shares
GET /json/call/get-collaborators
GET /json/call/filler-terms
GET /json/call/all-phrase-groups-previews
GET /json/call/search
GET /json/call/search-transcript
POST /json/call/segment-start
POST /json/call/segment-update
```

### 4. **Conversations & Search**
```
GET /conversations
GET /conversations/ajax/picklist-filter-data
GET /conversations/ajax/uploaded-calls
GET /conversations/ajax/read-participant-recent-searches
GET /conversations/ajax/participants-suggestions
POST /conversations/ajax/results
POST /conversations/ajax/histogram
POST /conversations/ajax/saved-query/descriptive
POST /conversations/ajax/insert-filter-recent-search
```

### 5. **Engage & Prospecting**
```
GET /engage/to-dos
GET /engagewebapi/ajax/engage/users
GET /engagewebapi/ajax/engage-gql-schema/get-schema-request
GET /engagewebapi/ajax/ae-home/start-of-today
GET /engagewebapi/ajax/ae-home/contacts/opt-out/channels
GET /engagewebapi/ajax/ae-home/prospecting/accounts-list/contacts
GET /engagewebapi/ajax/ae-home/crm/user-preferences
GET /engagewebapi/ajax/ae-home/is-owner-of-open-deals
GET /engagewebapi/ajax/ae-home/get-deals-list
POST /engagewebapi/ajax/ae-home/get-filtered-deals-list
POST /engagewebapi/ajax/assisted-selling/reminders
GET /engagewebapi/ajax/assisted-selling/reminders/count
POST /engagewebapi/ajax/filter-people
POST /engagewebapi/ajax/prospecting/prospects-by-crm-id
POST /engagewebapi/ajax/prospecting/engagements-data-for-prospect
GET /engagewebapi/ajax/prospecting/flow-settings/multi-flow-settings
GET /engagewebapi/ajax/prospecting/fields
GET /engagewebapi/ajax/prospecting/email-settings
```

### 6. **Email & Communication**
```
GET /emailcomposerwebapi/ajax/engage/emails-limits
GET /emailcomposerwebapi/ajax/email-composer-launcher/get-entity-email-status
GET /emailcomposerwebapi/ajax/email-templates/get-templates-tree
GET /emailcomposerwebapi/entity-attachments/import-email-attachment/get_upload_policy
GET /emailcomposerwebapi/entity-attachments/allowed-attachment-types
POST /emailcomposerwebapi/api/v1/mailbox/outbox
GET /engagewebapi/api/v1/mailbox/filters-meta
GET /emailcomposerwebapi/api/v1/snippets/tree
```

### 7. **Sequences & Automation**
```
GET /engagewebapi/ajax/sequences/get-sequence-tree
GET /engagewebapi/ajax/sequences/get-company-sequence-names
GET /engagewebapi/ajax/sequences-auto-assignment/get-metadata-for-rule
GET /engagewebapi/ajax/sequences-auto-assignment/get-rules
GET /engagewebapi/ajax/sequences-auto-assignment/get-company-rules
GET /tools/automations
```

### 8. **Deals & Forecast Management**
```
GET /deals
GET /deals/deals-forecast
GET /dealswebapi/ajax/deals/user-boards
GET /dealswebapi/ajax/deals/get-users
GET /dealswebapi/ajax/deals/board/editor/metadata
GET /dealswebapi/ajax/deals/boards
GET /dealswebapi/ajax/deals/settings
GET /dealswebapi/ajax/deals/user-connected-to-crm
GET /dealswebapi/ajax/deals/get-hidden-users-deal-data
POST /dealswebapi/ajax/deals/board/view/init
POST /dealswebapi/ajax/deals/get-board-totals
POST /dealswebapi/ajax/deals/get-board-deals
POST /dealswebapi/ajax/deals/get-board-people-totals-v2
POST /dealswebapi/ajax/deals/get-board-columns-totals
POST /dealswebapi/ajax/deals/get-timelines
POST /dealswebapi/deals/users/connectivity/all
GET /dealswebapi/ajax/deals/board/{id}
```

### 9. **Library & Content Management**
```
GET /library/private
GET /library/private/create-stream/{id}
GET /library/get-library-data
GET /library/read-folder
GET /callstream/get-all-subscriptions
GET /callstream/read-content
GET /callstream/read-details
POST /callstream/slack/get-slack-config-enabled
```

### 10. **Analytics & Statistics**
```
GET /insights/stats
GET /stats/ajax/get-seat
GET /stats/ajax/get-coaching-features
GET /stats/ajax/get-emails-features
GET /ajax/stats/get-users
POST /stats/ajax/v2/team/activity/aggregated/avgCallDuration
POST /stats/ajax/v2/team/activity/aggregated/avgWeeklyCalls
POST /stats/ajax/v2/team/activity/aggregated/avgWeeklyDuration
POST /stats/ajax/v2/team/activity/aggregated/totalCalls
POST /stats/ajax/v2/team/activity/aggregated/totalDuration
POST /stats/ajax/v2/team/activity/users/avgCallDuration
POST /stats/ajax/v2/team/activity/users/avgWeeklyCalls
POST /stats/ajax/v2/team/activity/users/avgWeeklyDuration
POST /stats/ajax/v2/team/topics/topicModels
POST /stats/ajax/v2/team/trackers/all
POST /stats/ajax/v2/team/trackers/users
```

### 11. **Coaching & Feedback**
```
GET /coaching/coaching-inbox
GET /ajax/coaching/coaching/get-feedback-data
GET /ajax/call-feedback
GET /call-scorecards
GET /call-answered-scorecards
```

### 12. **Company & Settings**
```
GET /company
GET /company/whisper/topics
GET /ajax/company/whisper/topics/list
GET /v2/company/product-catalog
GET /v2/company/full-product-catalog
```

### 13. **Integrations & Third-Party**
```
GET /ajax/installed-integrations
GET /ajax/third-party/rules
GET /ajax/sales-navigator/get-sales-navigator-settings
GET /slack/slack-data
GET /slack/slack-all-channels
GET /gongconnectwebapi/company-dialer/get-active-company-dialer
GET /gongconnectwebapi/gong-connect/twilio-access-token
GET /gongconnectwebapi/gong-connect/get-company-preferences
```

### 14. **Search & Discovery**
```
GET /search-box/ajax/read-recent-searches
POST /search-box/ajax/insert-recent-search
GET /ajax/ask-me-anything/questions
GET /ajax/ask-me-anything/get-call-data
GET /ajax/account/ask-me-anything/fetch-answer/v3
```

### 15. **Resource & Media Management**
```
GET /resource.gcell-nam-01.app.gong.io/resourceproxywebapi/resource (154 calls)
GET /resource.gcell-nam-01.app.gong.io/e/signed/resource (34 calls)
GET /bravo-17.gcell-nam-01.app.gong.io/resourceproxywebapi/resource (8 calls)
GET /alpha-10.gcell-nam-01.app.gong.io/resourceproxywebapi/resource (1 call)
```

## 🔧 **Technical Implementation Details**

### Base URLs
- **Primary**: `https://us-14496.app.gong.io`
- **Authentication**: `https://app.gong.io`
- **Resources**: `https://resource.gcell-nam-01.app.gong.io`
- **Streaming**: `https://gcell-nam-01.streams.gong.io`

### Common Parameters
- `workspace-id={workspace_id}` - Workspace identifier
- `company-id={company_id}` - Company identifier  
- `call-stream-id={call_stream_id}` - Call stream identifier
- `folder-id={folder_id}` - Folder identifier
- `from-date=` & `to-date=` - Date range filters

### Authentication Patterns
- Session-based authentication with RTKN tokens
- SAML integration via Okta
- JWT tokens for resource access
- Key store access (KSA) for secure operations

### Response Formats
- **JSON**: Primary format for API responses
- **HTML**: For page content and forms
- **Binary**: For media resources and files

## 🎯 **High-Value Endpoints for Toolkit Development**

### Priority 1: Core Data Extraction
1. **Calls**: `/ajax/home/calls/my-calls`, `/json/call/search`
2. **Contacts**: `/ajax/contacts/get-single-contact-details`
3. **Accounts**: `/ajax/account`, `/ajax/account/people`
4. **Deals**: `/dealswebapi/ajax/deals/get-board-deals`
5. **Activities**: `/ajax/account/day-activities`

### Priority 2: Advanced Features
1. **Conversations**: `/conversations/ajax/results`
2. **Analytics**: `/stats/ajax/v2/team/activity/aggregated/*`
3. **Coaching**: `/ajax/coaching/coaching/get-feedback-data`
4. **Library**: `/library/get-library-data`
5. **Sequences**: `/engagewebapi/ajax/sequences/get-sequence-tree`

### Priority 3: Integration Support
1. **CRM Sync**: `/engagewebapi/ajax/crm-object-last-sync-time`
2. **Third-party**: `/ajax/installed-integrations`
3. **Slack**: `/slack/slack-data`
4. **Email**: `/emailcomposerwebapi/api/v1/mailbox/outbox`

## 📈 **Performance Characteristics**

### High-Frequency Endpoints (>10 calls)
- `/ajax/common/rtkn` (34 calls) - Session management
- `/ajax/common/ksa` (18 calls) - Key store access
- `/r/js/jquery/*` (17 calls) - JavaScript libraries
- `/gongconnectwebapi/*` (17+ calls) - Dialer integration
- `/userjourneywebapi/inline-alerts` (15 calls) - User notifications

### Resource-Intensive Endpoints
- `/resource.gcell-nam-01.app.gong.io/resourceproxywebapi/resource` (154 calls)
- `/cdn-cgi/rum` (52 calls) - Real user monitoring
- `/r/js/dist/*` - Static assets and JavaScript bundles

## 🔐 **Security Considerations**

### Authentication Requirements
- All API endpoints require valid session authentication
- Resource endpoints use signed tokens
- CSRF protection via RTKN tokens
- Rate limiting likely in place for high-frequency endpoints

### Data Sensitivity
- **High**: Call recordings, transcripts, customer data
- **Medium**: Analytics, coaching feedback, deal information  
- **Low**: Static assets, configuration data

## 🚀 **Recommended Toolkit Implementation Strategy**

### Phase 1: Core Data Access
1. Implement session management with RTKN tokens
2. Build contact and account data extractors
3. Add call and conversation data access
4. Create basic deal and opportunity extraction

### Phase 2: Advanced Features
1. Add analytics and reporting capabilities
2. Implement coaching and feedback extraction
3. Build sequence and automation data access
4. Add library and content management

### Phase 3: Integration & Optimization
1. Add CRM synchronization support
2. Implement third-party integration data
3. Optimize for performance and rate limiting
4. Add comprehensive error handling

---

**Note**: This documentation is based on live HAR capture analysis and represents actual API usage patterns. All endpoints have been validated as returning HTTP 200 status codes during the capture session.