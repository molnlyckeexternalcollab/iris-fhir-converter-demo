---
publisher: "epic.com"
title: "Documentation - Epic on FHIR"
url: "https://fhir.epic.com/Documentation?docId=cds-hooks"
lang: "en"
tooling: "https://microlink.io/tools/url-to-markdown"
---

## Table of Contents

- [CDS Hooks Tutorial](#cds-hooks-tutorial-1)
- [Introduction](#introduction-1)
  - [Guidance to CDS Developers](#guidance-to-cds-developers)
- [Hooks](#hooks)
  - [patient-view](#patient-view)
  - [order-select](#order-select)
  - [order-sign](#order-sign)
- [CDS Hooks Request](#cds-hooks-request)
  - [Prefetch](#prefetch)
  - [Input Fields for JSON POST Body](#input-fields-for-json-post-body)
  - [Epic Extensions](#epic-extensions)
  - [Example HTTP Request](#example-http-request)
- [CDS Hooks Response](#cds-hooks-response)
  - [Suggestion or app launch?](#suggestion-or-app-launch)
  - [Actions](#actions)
  - [HTTP Response Fields](#http-response-fields)
  - [Card Attributes](#card-attributes)
  - [Suggestion Attributes](#suggestion-attributes)
  - [Codesets for Create APIs](#codesets-for-create-apis)
  - [Link Attributes](#link-attributes)
  - [Supported Extensions](#supported-extensions)
  - [Basic Example HTTP Response with Card](#basic-example-http-response-with-card)
  - [Example HTTP Response for no decision support needed](#example-http-response-for-no-decision-support-needed)
  - [Example HTTP Response with Links, Override Reasons, and Suggestions](#example-http-response-with-links-override-reasons-and-suggestions)
- [Trusting CDS Clients](#trusting-cds-clients)
  - [JWT Tokens](#jwt-tokens)
  - [Install Considerations for the JWT Token](#install-considerations-for-the-jwt-token)
- [Feedback](#feedback)
- [Medication References](#medication-references)
  - [Example Medication Reference](#example-medication-reference)
- [Implementing CDS Hooks with an Epic Organization](#implementing-cds-hooks-with-an-epic-organization)
- [Gotchas](#gotchas)
  - [Event Notification Streaming](#event-notification-streaming)
  - [FHIR Version](#fhir-version)
  - [Required OAuth 2.0 Scopes](#required-oauth-20-scopes)
  - [Pre-Registration of Links and SMART Apps](#pre-registration-of-links-and-smart-apps)
  - [Endpoint URI Validation](#endpoint-uri-validation)

---

### CDS Hooks Tutorial

## CDS Hooks Tutorial

## Introduction

Clinical Decision Support (CDS) Hooks is an HL7 standard for in-workflow decision support integrations between electronic health record systems and remote, real-time, provider-facing decision support services. This tutorial describes Epic’s support for this standard.

Epic’s support for CDS Hooks is built on a workflow engine and CDS rule engine. Organizations using Epic can configure native CDS alerts by defining the workflow point at which they are triggered, known as the hook, and the criteria to evaluate when they are triggered. These criteria determine whether a CDS alert appears to the clinician and, if it does, what information it contains. Epic’s implementation of CDS Hooks enables native criteria to call a remote CDS Hooks API when evaluating whether to show a CDS alert. In Epic, the native CDS alert is referred to as an OurPractice Advisory (OPA).

### Guidance to CDS Developers

CDS Hooks is a powerful integration technology because it directly interacts with clinician workflows. Treat the ability to interact with clinicians carefully. As a CDS developer, you now share responsibility for a positive user experience. Your CDS service must be fast, must avoid alert fatigue, and should improve over time.

## Hooks

As of Epic version May 2021, Epic primarily supports three standard hooks built on pre-existing CDS alert workflow triggers. Note that Epic supports many more native workflow triggers than CDS Hooks has standardly defined.

### patient-view

The patient-view hook is triggered in two scenarios:

1.  When a patient’s chart is opened. The native Epic trigger is named Open Patient Chart. Epic recommends against firing a CDS Hooks request every time a patient chart is opened because it results in a poor user experience. Instead, work with the health system to use this trigger in combination with more specific, native business criteria in Epic to limit the number of CDS Hooks requests.
2.  When a native Epic trigger calls a CDS Hooks service that is not standardized by CDS Hooks. For example, Enter Allergy is a native Epic workflow trigger that an organization can configure to show an OPA, including evaluating criteria that calls a CDS Hooks service. Because there is no industry standard hook for the Enter Allergy workflow step, we reuse the patient-view hook. The Epic-specific "com.epic.cdshooks.request.bpa-trigger-action" extension (see below) can be used to differentiate between native Epic triggers.

### order-select

Epic supports the order-select hook in workflows when a clinician enters orders for a patient. In addition to the new selection of one or more orders (which triggers the order-select event), the clinician might have already selected other orders that have not yet been signed. The draftOrders JSON object contains a bundle of both the newly selected orders and the previously selected, unsigned orders. The "selections" array of FHIR identifiers identifies which of the unsigned orders from the draftOrders bundle are newly selected. Decision support using this hook should focus on the newly selected orders.

The draftOrders bundle can contain the MedicationRequest, ServiceRequest, or ProcedureRequest resource.

### order-sign

The order-sign hook is triggered in Epic as the final step in the ordering process. It occurs after a clinician has clicked the Sign Orders button, but before the system has finalized the order. Decision support from this hook is the final chance for the clinician to revise the order. This hook allows for collection of all unsigned order details to send in the CDS Hooks call as MedicationRequest, ServiceRequest, or ProcedureRequest resources.

## CDS Hooks Request

### Prefetch

Prefetch can be a valuable method for optimizing the performance of your CDS service. Evaluate whether you can collect the data needed to inform your CDS service using the CDS Hooks prefetch model.

Prefetch within Epic can be configured in your CDS Hooks service’s OurPractice Advisory (LGL) record. Any resource that you’d like to prefetch must be appropriately scoped to your client and match the client’s primary FHIR version. Epic does not support automatically retrieving the contents of a CDS Hooks service's discovery endpoint.

Here is an example of how prefetch might be configured for a CDS service:

|                        |                                                                                                        |
| ---------------------- | ------------------------------------------------------------------------------------------------------ |
| Prefetch Property Name | FHIR Query                                                                                             |
| patient                | Patient/{{context.patientId}}                                                                          |
| medications            | MedicationRequest?patient={{context.patientId}}&status=active                                          |
| encounterDx            | Condition?patient={{context.patientId}}&encounter={{context.encounterId}}&category=encounter-diagnosis |
| user                   | {{context.userId}}                                                                                     |

Note that the **{{context.patientId}}**, **{{context.encounterId}}**, and **{{context.userId}}** prefetch tokens are all used here. These IDs are returned by default in the CDS Hooks request context field and are also available to use in constructing contextual read/search FHIR requests that are included in the initial request to the CDS Hooks service. In contrast to the FHIR IDs, which are always sent in the context, the patient prefetch property defined above returns the entire patient resource within the prefetch. For searches, the medications and encounterDx prefetch properties above show how to use prefetch tokens as query parameters when implementing your CDS Hooks service.

The **{{context.userId}}** prefetch token is unique in that it returns both a FHIR resource name and FHIR resource ID. If the clinician triggering the CDS Hooks request has a provider record in Epic, the request returns "PractitionerRole/ ". If the clinician does not have a provider record, the request returns "Practitioner/ ". Additionally, the **{{userPractitionerId}}** and **{{userPractitionerRoleId}}** prefetch tokens can be used in prefetch to return the FHIR resource ID for their respective resources.

### Input Fields for JSON POST Body

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>Field</strong></p></td>
<td><p><strong>Description</strong></p></td>
</tr>
<tr>
<td><p><strong>hook</strong></p></td>
<td><p>Epic supports the following hooks:</p>

<ul>
<li>order-select</li>
<li>order-sign</li>
<li>patient-view</li>
</ul>
</td>
</tr>
<tr>
<td><p><strong>hookInstance</strong></p></td>
<td><p>A universally unique identifier (UUID) for each hook call.</p></td>
</tr>
<tr>
<td><p><strong>fhirServer</strong></p></td>
<td><p>The base FHIR URL for the health system. Epic will always provide this. Reach out to the Client Systems Web and Server Systems team or EDI TS for the organization to obtain this.</p></td>
</tr>
<tr>
<td><p><strong>fhirAuthorization</strong></p></td>
<td><p>A structure holding an OAuth 2.0 bearer access token, which can be used to authenticate to Epic APIs for a short period of time.</p></td>
</tr>
<tr>
<td><p><strong>context</strong></p></td>
<td><p>The CDS Hooks specification (for example, [patient-view](https://cds-hooks.hl7.org/hooks/patient-view/STU1/patient-view/)) defines the context elements associated with each hook. Epic always sends patientId and userId.<br />
If the hook is initiated from an encounter context, encounterId is sent.<br />
For the order-select and order-sign hooks, draftOrders is always sent. Specific to order-select, the selections array identifies which orders are newly selected.</p></td>
</tr>
<tr>
<td><p><strong>prefetch</strong></p></td>
<td><p>Resources sent in the prefetch are configured by the health system and can include FHIR resources that are [already supported by Epic.](https://fhir.epic.com/)</p></td>
</tr>
</tbody>
</table>

### Epic Extensions

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>Extension</strong></p></td>
<td><p><strong>Description</strong></p></td>
</tr>
<tr>
<td><p><strong>com.epic.cdshooks.request.bpa-trigger-action</strong></p></td>
<td><p>The specific trigger action in Epic that is mapped to the hook. Common values include, but are not limited to:</p>

<ul>
<li>5 (General OPA section)</li>
<li>6 (Enter problem)</li>
<li>7 (Enter diagnosis)</li>
<li>18 (Enter order)</li>
<li>23 (Sign orders)</li>
<li>26 (IP Admission OPA section)</li>
<li>27 (IP Discharge OPA section)</li>
<li>29 (IP Transfer OPA section)</li>
<li>60 (Open patient chart)</li>
</ul>
</td>
</tr>
<tr>
<td><p><strong>com.epic.cdshooks.request.cds-hooks-specification-version</strong></p></td>
<td><p>The CDS hooks specification version used by Epic.</p></td>
</tr>
<tr>
<td><p><strong>com.epic.cdshooks.request.fhir-version</strong></p></td>
<td><p>The primary FHIR version of the CDS service as specified during OAuth registration.</p></td>
</tr>
<tr>
<td><p><strong>com.epic.cdshooks.request.criteria-id</strong></p></td>
<td><p>The ID of the OPA criteria record in Epic. This value can be helpful during troubleshooting.</p></td>
</tr>
<tr>
<td><p><strong>com.epic.cdshooks.request.epic-version</strong></p></td>
<td><p>The version of Epic that the health system is currently using.</p></td>
</tr>
<tr>
<td><p><strong>com.epic.cdshooks.request.cds-hooks-implementation-version</strong></p></td>
<td><p>The internal version Epic assigns to CDS Hooks implementations. Can be used to determine what features are supported.</p></td>
</tr>
</tbody>
</table>

### Example HTTP Request

```json
{
  "hookInstance": "f399c67c-c703-11ea-af16-460231621f93",
  "fhirServer": "https://example.com/interconnect-instance-oauth/api/FHIR/R4",
  "hook": "patient-view",
  "fhirAuthorization": {
    "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJ1cm46ZXBpYzpjZWMuY2RlIiwiY2xpZW50X2lkIjoiYWVhYzNkYTctNjQ4MS00NWFmLWFkNDEtNDJlNWU3MDExNDFkIiwiZXBpYy5lY2kiOiJ1cm46ZXBpYzpDdXJyZW50LURldmVsb3BtZW50LUVudmlyb25tZW50IiwiZXBpYy5tZXRhZGF0YSI6Ik4yTDdoSFE3clNxLXdQbkstcVMyZlBTSjY1Q1EzS1ZOVHhhTUlBZGRVTllwemQyOEE0Q2d4ZHA0SVg0NUI5YmE4TVVJdEl1NkEzYjBkYmU1c1ZlY093V1ZZN0tTd2VZb09KZDR5R2hmblcxdk9yOENoX195N2NrT1VtV005cnVhIiwiZXBpYy50b2tlbnR5cGUiOiJhY2Nlc3MiLCJleHAiOjE1OTQ4NjMzMzcsImlhdCI6MTU5NDg2MzAzNywiaXNzIjoidXJuOmVwaWM6Y2VjLmNkZSIsImp0aSI6ImU4MjFhMDA5LTgzNjAtNDRkYy1iZmMwLTEyZmU4ODA3MjQyYSIsIm5iZiI6MTU5NDg2MzAzNywic3ViIjoiZUJxZ0Foc2pVcHF3a3lJWm9LZU1jVUEzIn0.hF2Ir9717QxJ0TgiFXKN1bhRdicgUHEf_0tjZ7qiy2Enzsn7_dW4HaueJqg22vcnrEayLxlW4h6Q6J5He3-U7VXmGBFd5AKXxVLbTQZupN6x4owt5n_N1OJKDu5UVJdlWoq-fBVn2sEyDfvITQ-BK21MWXxGaEcnttJNxS0Mk847JnxBby2oLzAd5NnIbdT733S2nL36ViK_mVnkucLu4vxwVRcaec2zCpvqF8Pn2Crl3yKaPKQbRqc6y12hprdUeB2VxOm3H5KxJQKYnEGTKNCmCy5w3Yaz86KtP9OlX1e3n6Km3TSCtZbj0Gm7QIVyDARAlREPA_XzbgQ3ItJang",
    "token_type": "Bearer",
    "expires_in": 300,
    "scope": "ALLERGYINTOLERANCE.READ ALLERGYINTOLERANCE.SEARCH Observation.Read (Smoking History) Observation.Read (Labs) (R4) Observation.Read (Vitals) Observation.Read (Vitals) (R4) Observation.Search (Labs) (R4) Observation.Search (Smoking History) Observation.Search (Vitals) Observation.Search (Vitals) (R4) Practitioner.Read (R4) Practitioner.Search (DSTU2) PROCEDURE.READ PROCEDURE.SEARCH MedicationRequest.Read (R4) MedicationRequest.Search (R4) CONDITION.READ CONDITION.SEARCH Condition.Read (R4) Condition.Search (R4) PATIENT.READ PATIENT.SEARCH PRACTITIONER.READ PRACTITIONER.SEARCH OBSERVATION.READ OBSERVATION.SEARCH urn:Epic-com:Informatics.2014.Services.Order.AnnotateOrders AllergyIntolerance.Search (R4) AllergyIntolerance.Read (R4) Patient.Read (R4) Patient.Search (R4) Location.Read (R4) Encounter.Read (R4) Encounter.Search (R4) urn:Epic-com:Core.2016.Services.DataUtility.GetImportDataLog Condition.Create (R4) Medication.Read (R4) MEDICATION.READ (DSTU2) MEDICATION.READ MEDICATIONORDER.READ MEDICATIONORDER.READ (DSTU2) MEDICATIONORDER.SEARCH MEDICATION.SEARCH MedicationStatement.Read (R4) MEDICATIONSTATEMENT.READ (DSTU2) MEDICATIONSTATEMENT.READ MEDICATIONSTATEMENT.SEARCH MedicationStatement.Search (R4) Condition.Search (R4) Patient.Read (R4) Practitioner.Read (R4) Patient.Search (R4) Practitioner.Search (R4) Condition.Read (R4) Condition.Create (R4) AllergyIntolerance.Read (R4) AllergyIntolerance.Search (R4) Observation.Read (R4) Observation.Search (R4) Practitioner.Search (R4) PractitionerRole.Search (R4) PractitionerRole.Search (R4) medication medication.create Encounter.Read (R4) Encounter.Search (R4) ProcedureRequest.Read (R4) ProcedureRequest.Search (R4) EPIC.FHIR.R4.SERVICES.MEDICATIONREQUEST.CREATE EPIC.FHIR.R4.SERVICES.MEDICATIONREQUEST.CREATE Condition.Create (Encounter Diagnosis) (R4) Condition.Create (Problems) (R4) EPIC.FHIR.R4.SERVICES.PROCEDUREREQUEST.CREATE EPIC.FHIR.R4.SERVICES.SERVICEREQUEST.CREATE Condition.Read (Encounter Diagnosis) (R4) Condition.Read (Health Concern) (R4) Condition.Read (Problems) (R4) Condition.Search (Encounter Diagnosis) (R4) Condition.Search (Health Concern) (R4) Condition.Search (Problems) (R4) Observation.Read (Core Characteristics) (R4) Observation.Read (Labs) (R4) Observation.Read (LDA-W) (R4) Observation.Read (Obstetric Details) (R4) Observation.Read (Smoking History) (R4) Observation.Read (Vitals) (R4) Observation.Search (Core Characteristics) (R4) Observation.Search (Labs) (R4) Observation.Search (LDA-W) (R4) Observation.Search (Obstetric Details) (R4) Observation.Search (Smoking History) (R4) Observation.Search (Vitals) (R4) MedicationRequest.Read (R4) MedicationRequest.Search (R4) condition.create(diagn Condition.Create Problem (R4) PractitionerRole.Read (R4) PractitionerRole.Read (R4)",
    "subject": "aeac3da7-6481-45af-ad41-42e5e701141d"
  },
  "context": {
    "patientId": "eXoGxqgBaJuNkuahMYmiDhg3",
    "encounterId": "eFyoeOuWgXtlQmOQzPdkQWwy3s8a49yrUc-LtjwhWT6g3",
    "userId": "PractitionerRole/e-QokEGUJIzyynNdkCFrs9w3"
  },
  "prefetch": {
    "-user": {
      "resourceType": "PractitionerRole",
      "id": "e-QokEGUJIzyynNdkCFrs9w3",
      "active": true,
      "practitioner": {
        "reference": "https://example.com/interconnect-instance-oauth/api/FHIR/R4/Practitioner/eqZb1t82mP4YeBjiLldSFPQ3",
        "display": "Family Medicine Physician"
      },
      "code": [
        {
          "coding": [
            {
              "system": "urn:oid:1.2.840.114350.1.13.861.1.7.10.836982.1040",
              "code": "1",
              "display": "Physician"
            }
          ],
          "text": "Physician"
        }
      ],
      "specialty": [
        {
          "coding": [
            {
              "system": "urn:oid:1.2.840.114350.1.72.1.7.7.10.688867.4160",
              "code": "10",
              "display": "Cardiology"
            }
          ],
          "text": "Cardiology"
        },
        {
          "coding": [
            {
              "system": "urn:oid:1.2.840.114350.1.72.1.7.7.10.688867.4160",
              "code": "5",
              "display": "Anesthesiology"
            }
          ],
          "text": "Anesthesiology"
        },
        {
          "coding": [
            {
              "system": "urn:oid:1.2.840.114350.1.72.1.7.7.10.688867.4160",
              "code": "15",
              "display": "Dermatology"
            }
          ],
          "text": "Dermatology"
        },
        {
          "coding": [
            {
              "system": "urn:oid:1.2.840.114350.1.72.1.7.7.10.688867.4160",
              "code": "18",
              "display": "Endocrinology"
            }
          ],
          "text": "Endocrinology"
        }
      ]
    },
    "patient": {
      "resourceType": "Patient",
      "id": "eXoGxqgBaJuNkuahMYmiDhg3",
      "extension": [
        {
          "extension": [
            {
              "valueCoding": {
                "system": "http://hl7.org/fhir/us/core/ValueSet/omb-race-category",
                "code": "UNK",
                "display": "Unknown"
              },
              "url": "ombCategory"
            },
            {
              "valueString": "Unknown",
              "url": "text"
            }
          ],
          "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race"
        },
        {
          "extension": [
            {
              "valueCoding": {
                "system": "http://hl7.org/fhir/us/core/ValueSet/omb-ethnicity-category",
                "code": "UNK",
                "display": "Unknown"
              },
              "url": "ombCategory"
            },
            {
              "valueString": "Unknown",
              "url": "text"
            }
          ],
          "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity"
        },
        {
          "valueCode": "M",
          "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-birthsex"
        }
      ],
      "identifier": [
        {
          "use": "usual",
          "type": {
            "text": "EPI"
          },
          "system": "urn:oid:1.2.840.114350.1.1",
          "value": "113822"
        },
        {
          "use": "usual",
          "type": {
            "text": "EXTERNAL"
          },
          "value": "Z16282"
        },
        {
          "use": "usual",
          "type": {
            "text": "FHIR"
          },
          "value": "TDjw8.slp7UtBKr3jNvYPsSGUb0qoZMC5OEhD5iu5ticB"
        },
        {
          "use": "usual",
          "type": {
            "text": "FHIR R4"
          },
          "value": "eXoGxqgBaJuNkuahMYmiDhg3"
        },
        {
          "use": "usual",
          "type": {
            "text": "INTERNAL"
          },
          "value": "    Z16282"
        },
        {
          "use": "usual",
          "system": "urn:oid:2.16.840.1.113883.4.1"
        }
      ],
      "active": true,
      "name": [
        {
          "use": "official",
          "text": "Family Medicine Physician",
          "family": "Physician",
          "given": [
            "Family Medicine"
          ]
        },
        {
          "use": "usual",
          "text": "Family Medicine Physician",
          "family": "Physician",
          "given": [
            "Family Medicine"
          ]
        }
      ],
      "gender": "male",
      "birthDate": "1981-06-24",
      "deceasedBoolean": false,
      "managingOrganization": {
        "reference": "https://example.com/interconnect-instance-oauth/api/FHIR/R4/Organization/e1aU.Joccsz0IPnyexqMjXw3",
        "display": "EXAMPLE ORGANIZATION"
      }
    },
    "conditions": {
      "resourceType": "Bundle",
      "type": "searchset",
      "total": 0,
      "link": [
        {
          "relation": "self",
          "url": "https://example.com/interconnect-instance-oauth/api/FHIR/R4/Condition?patient=eXoGxqgBaJuNkuahMYmiDhg3&_include=Condition:patient&_include=Condition:patient:organization"
        }
      ],
      "entry": [
        {
          "resource": {
            "resourceType": "OperationOutcome",
            "issue": [
              {
                "severity": "warning",
                "code": "processing",
                "details": {
                  "coding": [
                    {
                      "system": "urn:oid:1.2.840.114350.1.13.861.1.7.2.657369",
                      "code": "4101",
                      "display": "Resource request returns no results."
                    }
                  ],
                  "text": "Resource request returns no results."
                }
              }
            ]
          },
          "search": {
            "mode": "outcome"
          }
        }
      ]
    },
    "medications": {
      "resourceType": "Bundle",
      "type": "searchset",
      "total": 2,
      "link": [
        {
          "relation": "self",
          "url": "https://example.com/interconnect-instance-oauth/api/FHIR/R4/MedicationRequest?patient=eXoGxqgBaJuNkuahMYmiDhg3"
        }
      ],
      "entry": [
        {
          "link": [
            {
              "relation": "self",
              "url": "https://example.com/interconnect-instance-oauth/api/FHIR/R4/MedicationRequest/e4jAeTRRFdgN-QzpjNRbwQkDnp1BQlqrukNdC6BvYzU43"
            }
          ],
          "fullUrl": "https://example.com/interconnect-instance-oauth/api/FHIR/R4/MedicationRequest/e4jAeTRRFdgN-QzpjNRbwQkDnp1BQlqrukNdC6BvYzU43",
          "resource": {
            "resourceType": "MedicationRequest",
            "id": "e4jAeTRRFdgN-QzpjNRbwQkDnp1BQlqrukNdC6BvYzU43",
            "identifier": [
              {
                "use": "usual",
                "system": "urn:oid:1.2.840.114350.1.13.861.1.7.2.798268",
                "value": "1000182255"
              }
            ],
            "status": "active",
            "intent": "order",
            "category": {
              "coding": [
                {
                  "system": "http://hl7.org/fhir/medication-request-category",
                  "code": "inpatient",
                  "display": "Inpatient"
                }
              ],
              "text": "Inpatient"
            },
            "medicationReference": {
              "reference": "https://example.com/interconnect-instance-oauth/api/FHIR/R4/Medication/ehjM3OtjgdW8Bea3jIQgMFVhzPMcMELCBS5v775xzbLetNaOP5vZRG-7BUwFy1hYFzJ7rXwELBf63P6zbB4tI56DXbUTYtEZEWyFIzxmyONE3",
              "display": "IBUPROFEN 200 MG PO TABS"
            },
            "subject": {
              "reference": "https://example.com/interconnect-instance-oauth/api/FHIR/R4/Patient/eXoGxqgBaJuNkuahMYmiDhg3",
              "display": "Physician, Family Medicine"
            },
            "authoredOn": "2020-07-06T20:25:56Z",
            "recorder": {
              "reference": "https://example.com/interconnect-instance-oauth/api/FHIR/R4/Practitioner/eqZb1t82mP4YeBjiLldSFPQ3",
              "display": "Family Medicine Physician"
            },
            "dosageInstruction": [
              {
                "extension": [
                  {
                    "valueQuantity": {
                      "value": 2,
                      "unit": "tablet",
                      "system": "http://unitsofmeasure.org",
                      "code": "{tbl}"
                    },
                    "url": "https://open.epic.com/fhir/extensions/admin-amount"
                  },
                  {
                    "valueQuantity": {
                      "value": 400,
                      "unit": "mg",
                      "system": "http://unitsofmeasure.org",
                      "code": "mg"
                    },
                    "url": "https://open.epic.com/fhir/extensions/ordered-dose"
                  }
                ],
                "timing": {
                  "repeat": {
                    "boundsPeriod": {
                      "start": "2020-07-06T20:25:32Z"
                    },
                    "frequency": 1,
                    "period": 6,
                    "periodUnit": "h"
                  },
                  "code": {
                    "text": "Q6H PRN"
                  }
                },
                "asNeededBoolean": true,
                "route": {
                  "coding": [
                    {
                      "system": "urn:oid:1.2.840.114350.1.13.861.1.7.4.798268.7025",
                      "code": "15",
                      "display": "Oral"
                    },
                    {
                      "system": "http://snomed.info/sct",
                      "code": "260548002",
                      "display": "Oral"
                    }
                  ],
                  "text": "Oral"
                },
                "doseQuantity": {
                  "value": 400,
                  "unit": "mg",
                  "system": "http://unitsofmeasure.org",
                  "code": "mg"
                }
              }
            ]
          },
          "search": {
            "mode": "match"
          }
        },
        {
          "link": [
            {
              "relation": "self",
              "url": "https://example.com/interconnect-instance-oauth/api/FHIR/R4/MedicationRequest/es5s.w.VqTbI-3sTtgDY0f.oJSZ8leYTXykPvcBCZrWQ3"
            }
          ],
          "fullUrl": "https://example.com/interconnect-instance-oauth/api/FHIR/R4/MedicationRequest/es5s.w.VqTbI-3sTtgDY0f.oJSZ8leYTXykPvcBCZrWQ3",
          "resource": {
            "resourceType": "MedicationRequest",
            "id": "es5s.w.VqTbI-3sTtgDY0f.oJSZ8leYTXykPvcBCZrWQ3",
            "identifier": [
              {
                "use": "usual",
                "system": "urn:oid:1.2.840.114350.1.13.861.1.7.2.798268",
                "value": "1000182291"
              }
            ],
            "status": "active",
            "intent": "order",
            "category": {
              "coding": [
                {
                  "system": "http://hl7.org/fhir/medication-request-category",
                  "code": "inpatient",
                  "display": "Inpatient"
                }
              ],
              "text": "Inpatient"
            },
            "medicationReference": {
              "reference": "https://example.com/interconnect-instance-oauth/api/FHIR/R4/Medication/eIBy3xFZsuXmpUpNLdojkXC2jhRNQyq0NyjvMBlrASIS4dl.7I3naftOtzE1KVToZwnuJ5ty7Zonwkhzz9kHIeEYjUV102TvDEv7zaGJFkKQ3",
              "display": "MITOMYCIN 40 MG IV SOLR"
            },
            "subject": {
              "reference": "https://example.com/interconnect-instance-oauth/api/FHIR/R4/Patient/eXoGxqgBaJuNkuahMYmiDhg3",
              "display": "Physician, Family Medicine"
            },
            "authoredOn": "2020-07-06T20:40:24Z",
            "recorder": {
              "reference": "https://example.com/interconnect-instance-oauth/api/FHIR/R4/Practitioner/eqZb1t82mP4YeBjiLldSFPQ3",
              "display": "Family Medicine Physician"
            },
            "dosageInstruction": [
              {
                "extension": [
                  {
                    "valueQuantity": {
                      "value": 10,
                      "unit": "mg",
                      "system": "http://unitsofmeasure.org",
                      "code": "mg"
                    },
                    "url": "https://open.epic.com/fhir/extensions/ordered-dose"
                  }
                ],
                "timing": {
                  "repeat": {
                    "boundsPeriod": {
                      "start": "2020-07-06T23:00:00Z"
                    },
                    "frequency": 2,
                    "period": 1,
                    "periodUnit": "d"
                  },
                  "code": {
                    "text": "0900 & 1800"
                  }
                },
                "asNeededBoolean": false,
                "route": {
                  "coding": [
                    {
                      "system": "urn:oid:1.2.840.114350.1.13.861.1.7.4.798268.7025",
                      "code": "11",
                      "display": "Intravenous"
                    }
                  ],
                  "text": "Intravenous"
                }
              }
            ]
          },
          "search": {
            "mode": "match"
          }
        }
      ]
    }
  },
  "extension": {
    "com.epic.cdshooks.request.bpa-trigger-action": "18",
    "com.epic.cdshooks.request.cds-hooks-specification-version": "1.0",
    "com.epic.cdshooks.request.fhir-version": "R4",
    "com.epic.cdshooks.request.criteria-id": "2852",
    "com.epic.cdshooks.request.epic-version": "9.4",
    "com.epic.cdshooks.request.cds-hooks-implementation-version": "1.0",
    "com.epic.cdshooks.request.cds-hooks-su-version": "0",
    "internal.epic.cdshooks.request.epic-emp-id": "17805"
  }
}
```

## CDS Hooks Response

Upon receiving a CDS Hooks request from Epic, a CDS Service should quickly and synchronously respond with a CDS Hooks response. Optionally, the CDS Service may query Epic's FHIR server to learn additional information before responding using the OAuth 2.0 access token provided in the fhirAuthorization attribute in the request.

Upon evaluating the CDS Hooks request (including the relevant information contained in the request, and any data retrieved) according to your app’s business logic, your application responds. This response determines whether content is displayed to end users and what that content should be. Possible types of content include one or more of:

- textual information
- suggested actions to be taken, such as adding diagnoses
- links to your SMART app or other web pages

### Suggestion or app launch?

Generally, launching and interacting with an app is more time-consuming and therefore more disruptive to a user's workflow than returning a suggestion. If your CDS recommendations can be fully determined with only the information provided in the CDS Hooks request and other APIs, you should return these suggestions in the CDS Hooks response.

If you are unable to determine recommendations with only the information from the CDS Hooks request and other APIs, a link to launch an app enables additional user interaction. The app launch link is returned in the CDS Hooks response. A card response is a one-time event. CDS Hooks suggestions can only be returned in a CDS Hooks response. An app launched from a CDS Hooks response can't use CDS Hooks APIs.

Generally, the user needs to manually click a link to launch your app. There's nothing forcing the user to do this, and therefore they may not.

Beginning in Aug 23, Epic supports an "auto-launch" feature, such that a CDS Service may inform the EHR in its CDS Hooks response that it's appropriate to auto-launch an app because, for example, there's no other CDS guidance in the card. In the case where the only content in a CDS Hooks' response is an app url, and there's no other cards or native CDS, Epic may auto-launch an app.

### Actions

In the CDS Hooks response, a CDS Service can suggest suggestions, which include one or more actions. An action creates or deletes a FHIR resource. For example, a CDS Service can recommend that a problem be added to the current patient’s problem list by returning a FHIR Condition resource and a card.suggestion.action.type of “create”. The list of suggestions supported by Epic are listed in the [API library](https://fhir.epic.com/Sandbox) (search for CDS Hooks).

**If using the MedicationRequest, ServiceRequest, or ProcedureRequest resources to create an unsigned order in Epic, order overrides are NOT set with information from the service response, even if additional order details are specified. All order details come from the default values defined on the medication record, procedure record, or preference list.** To use these CREATE resources to specify a preference list item, specify the system as "urn:com.epic.cdshooks.action.code.system.preference-list-item". The code, assigned while building the preference list, will be the corresponding key used to identifty a particular order on the preference list.

### HTTP Response Fields

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>Field</strong></p></td>
<td><p><strong>Description</strong></p></td>
</tr>
<tr>
<td><p><strong>cards</strong></p></td>
<td><p>An array of cards that provide any of the following:</p>

<ul>
<li>Information

<ul>
<li>Text to be shown to the user, optionally formatted as GitHub-flavored markdown, or with html markup if also providing an Epic-specific extension defining the content type.</li>
</ul>
</li>
<li>Suggestions

<p>Work with the health system to map the problem list items, encounter diagnoses, medications, procedures and/or multi-order sets.</p>
<ul>
<li>Containing CREATE actions for Condition resources, specifically Problems, or Encounter Diagnosis.</li>
<li>Medication single order follow-up suggestions with CREATE actions using MedicationRequest resources</li>
<li>Medication single order follow-up suggestions with DELETE actions using MedicationRequest resources</li>
<li>Procedure single order follow-up suggestions with CREATE actions using ProcedureRequest (STU3) or ServiceRequest (R4) resources</li>
<li>Procedure single order follow-up suggestions with DELETE actions using ProcedureRequest (STU3) or ServiceRequest (R4) resources</li>
<li>Order Set, SmartSet, Pathway or Express Lane multiple order follow-up suggestions with CREATE actions using ProcedureRequest (STU3) or ServiceRequest (R4) resources</li>
</ul>
</li>
<li>Links

<ul>
<li>Reference links do not require any additional configuration</li>
<li>SMART App links need to be added to the allowlist in Epic</li>
</ul>
</li>
</ul>
</td>
</tr>
<tr>
<td><p><strong>systemActions</strong></p></td>
<td><p>Beginning in Feb 24, Epic supports system actions to annotate orders via the ServiceRequest.Update (Unsigned Order) (R4) API.</p></td>
</tr>
</tbody>
</table>

### Card Attributes

Epic-specific nuances regarding Card attributes:

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>Field</strong></p></td>
<td><p><strong>Description</strong></p></td>
</tr>
<tr>
<td><p><strong>indicator</strong></p></td>
<td><p>The info, warning, and critical values can be mapped to Epic-specific values by the Epic application team for display.</p></td>
</tr>
<tr>
<td><p><strong>uuid</strong></p></td>
<td><p>Unique identifier, used for auditing and logging suggestions. This field is optional. However, it is required if you intend to receive feedback.</p></td>
</tr>
<tr>
<td><p><strong>selectionBehavior</strong></p></td>
<td><p>Only the value "any" is currently supported.</p></td>
</tr>
<tr>
<td><p><strong>detail</strong></p></td>
<td><p>A CDS Service may return content as mere plain text, as GitHub flavored markdown, or, with an Epic-specific extension, as html. (See "com.epic.cdshooks.card.detail.content-type" extension, below).</p></td>
</tr>
<tr>
<td><p><strong>source.topic.code</strong></p></td>
<td><p>Epic only supports alpha-numeric strings as the code of source.topic, for example: "Card123" or "869e7c5587e04d0da96a60a84b5b8eac". The value returned in source.topic.code is used for logging and auditing, and is returned to the CDS Service in the feedback request. <strong>Maximum Length: 100 Characters</strong><br />
<br />
Source.topic.code should be a static identifier representing the particular topic of a card. When an end user overrides a given card, their acknowledgment is associated with this identifier. If you want the end user's override to be respected on subsequent requests to your CDS service, the topic identifier should remain static if sending the same card content.</p></td>
</tr>
<tr>
<td><p><strong>links</strong></p></td>
<td><p>Allows your service to suggest a link to a user for additional information or a SMART app. Allowed links are allow-listed by the health system.</p></td>
</tr>
</tbody>
</table>

### Suggestion Attributes

Epic-specific nuances regarding Suggestions and Action attributes:

|                         |                                                                                                                                                                                                                                                              |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Field**               | **Description**                                                                                                                                                                                                                                              |
| **label**               | This field is not used, but is required.                                                                                                                                                                                                                     |
| **uuid**                | Unique identifier, used for auditing and logging suggestions. This field is optional. However, it is required if you intend to receive feedback.                                                                                                             |
| **isRecommended**       | *Boolean.* When there are multiple suggestions, allows a service to indicate that a specific suggestion is recommended from all the available suggestions on the card. In Epic, this is used to control whether the suggested action is pre-selected or not. |
| **actions**             | Epic only supports a single action per suggestion.                                                                                                                                                                                                           |
| **actions.type**        | For a given resource, confirm the action types supported in the [API Library](https://fhir.epic.com/Sandbox).                                                                                                                                                |
| **actions.description** | This value is the primary content of the OPA. A CDS Service may return content as plain text.                                                                                                                                                                |
| **actions.resource**    | The FHIR resource provided by the CDS Service representing the action to be suggested to the user. Check the [API Library](https://fhir.epic.com/Sandbox) to see what resources (and action types) are supported.                                            |

### Codesets for Create APIs

The following table calls out codesets that may be used when specifying a coding for a given Create action.

<table>
<colgroup>
<col style="width: 33%" />
<col style="width: 33%" />
<col style="width: 33%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>System</strong></p></td>
<td><p><strong>Description</strong></p></td>
<td><p><strong>Resource(s)</strong></p></td>
</tr>
<tr>
<td><p><strong>urn:com.epic.cdshooks.action.code.system.preference-list-item</strong></p></td>
<td><p>Used to order a specific preference list item.</p></td>
<td><p>MedicationRequest.Create</p>
<p>ServiceRequest.Create</p>
<p>ProcedureRequest.Create</p></td>
</tr>
<tr>
<td><p><strong>urn:com.epic.cdshooks.action.code.system.orderset-item</strong></p></td>
<td><p>Used to order a specific SmartSet, OrderSet, or Pathway.</p></td>
<td><p>ServiceRequest.Create</p>
<p>ProcedureRequest.Create</p></td>
</tr>
<tr>
<td><p><strong>urn:com.epic.cdshooks.action.code.system.cms-hcc</strong></p></td>
<td><p>Used to suggest a Visit Diagnosis through a CMS-HCC model.</p></td>
<td><p>Condition.Create</p></td>
</tr>
<tr>
<td><p><strong>urn:com.epic.cdshooks.action.code.system.hhs-hcc</strong></p></td>
<td><p>Used to suggest a Visit Diagnosis through a HHS-HCC model.</p></td>
<td><p>Condition.Create</p></td>
</tr>
<tr>
<td><p><strong>urn:oid:2.16.840.1.113883.6.90</strong></p></td>
<td><p>Used to suggest ICD-10 codes.</p></td>
<td><p>Condition.Create</p></td>
</tr>
<tr>
<td><p><strong>urn:oid:2.16.840.1.113883.6.69</strong></p></td>
<td><p>Used to suggest NDC codes.</p></td>
<td><p>MedicationRequest.Create</p></td>
</tr>
<tr>
<td><p><strong>urn:oid:2.16.840.1.113883.6.88</strong></p></td>
<td><p>Used to suggest by RxNorm code.</p></td>
<td><p>MedicationRequest.Create</p></td>
</tr>
</tbody>
</table>

### Link Attributes

|                    |                                                                                                                                   |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| **Attribute**      | **Description**                                                                                                                   |
| **label**          | This field is not used, but is required.                                                                                          |
| **url**            | The URL to load.                                                                                                                  |
| **type**           | This field is required, and may either be **absolute** or **smart**.                                                              |
| **appContext**     | This field is optional, and will share information from the CDS card with the subsequently launched SMART app.                    |
| **autolaunchable** | Supported by Epic beginning in Aug 23, this will autolaunch the SMART app if only one OPA requests an autolaunch at a given time. |

### Supported Extensions

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>Extension</strong></p></td>
<td><p><strong>Description</strong></p></td>
</tr>
<tr>
<td><p><strong>com.epic.cdshooks.card.detail.content-type</strong></p></td>
<td><p>If this is not set, or set to "text/markdown" or "text/markdown; variant=GitHub", Epic will treat it as GitHub Flavored Markdown<br />
Other options are "text/plain", "text/html", and "text/markdown; variant=CommonMark".</p></td>
</tr>
</tbody>
</table>

### Basic Example HTTP Response with Card

```json
{
  "cards": [
    {
      "summary": "Testing Informational Card",
      "detail": "* Suspected colorectal cancer. \n\n* Please add to patient's diagnoses.\n\nSuspected Bladder cancer. Please add to patient's diagnoses.",
      "indicator": "critical",
      "source": {
        "topic": {
          "code": "examplecode1"
        }
      },
    },]
}
```

### Example HTTP Response for no decision support needed

```json
{
  "cards": []
}
```

### Example HTTP Response with Links, Override Reasons, and Suggestions

When sending override reasons in your response, configuration must be completed within the CDS Hooks criteria record to map overrideReasons.code to released acknowledgment reasons. overrideReasons.system does not have to be a specific string; it can be any non-empty string.


```json
{
   "cards":[
      {
         "summary":"Example",
         "indicator":"info",
         "extension":{
            "com.epic.cdshooks.card.detail.content-type":"text/html"
         },
         "detail":"Another card to test suggestions",
         "source": {
            "label": "Clinical Inferences",
            "url": "https://www.example.com/",
            "icon": "file://example/CDSHooks/images/example.png",
            "topic": {
              "code": "BCSCard2",
              "system": "card-system",
              "display": "BCS Card 2"
            }
          },
          "links": [
            {
              "label": "Github",
              "url": "https://github.com",
              "type": "absolute"
            },
            {
              "label": "R4 SMART Example App",
              "url": "https://example.com/EpicSMARTApp/Default.aspx?appFhirVersion=R4",
              "type": "smart",
              "appContext": "%FNAME%-%EXTENSION;74901%-420fe522-193c-11eb-9552-460231621f93~!@#$%^&*()-+{}[]|\\"
            },
          ],
          "overrideReasons":[
            {
                "code":"patrefused",
                "system":"http://example.org/cds-services/fhir/CodeSystem/override-reasons",
                "display":"Patient refused"
            },
            {
                "code":"seecomment",
                "system":"http://example123.org/cds-services/fhir/CodeSystem/override-reasons",
            }
         ],
           "suggestions":[
           {
               "label":"Arthritis",
               "uuid": "cf72fe83-1eb9-410c-94aa-04ec98736388",
               "actions":[
                  {
                     "type":"create",
                     "description":"Arthritis",
                     "resource": {
                        "resourceType": "Condition",
                        "category": [
                          {
                            "coding": [
                              {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                                "code": "encounter-diagnosis",
                                "display": "Encounter diagnosis"
                              }
                            ],
                            "text": "Encounter diagnosis"
                          }
                        ],
                        "code": {
                          "coding": [
                            {
                              "system": "urn:com.epic.cdshooks.action.code.system.cms-hcc",
                              "code": "40",
                              "display": "Arthritis"
                            }
                          ],
                          "text": "Stomach ache"
                        }
                      },
                  }
               ]
            },
            {
               "label":"Stroke",
               "uuid": "12035ae1-5d60-4f58-b922-882140b98283",
               "actions":[
                  {
                     "type":"create",
                     "description":"Stroke",
                     "resource": {
                        "resourceType": "Condition",
                        "category": [
                          {
                            "coding": [
                              {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                                "code": "encounter-diagnosis",
                                "display": "Encounter diagnosis"
                              }
                            ],
                            "text": "Encounter diagnosis"
                          }
                        ],
                        "code": {
                          "coding": [
                            {
                              "system": "urn:com.epic.cdshooks.action.code.system.cms-hcc",
                              "code": "100",
                              "display": "Stroke"
                            }
                          ],
                          "text": "Stroke"
                        }
                      },
                  }
               ]
            },
            {
               "label":"Stroke",
               "uuid": "1a53ba14-a06b-4e82-bbb0-09ae01a75515",
               "actions":[
                  {
                     "type":"create",
                     "description":"Stroke prognosis",
                     "resource": {
                        "resourceType": "Condition",
                        "category": [
                          {
                            "coding": [
                              {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                                "code": "problem-list-item",
                                "display": "Problem List"
                              }
                            ],
                            "text": "Problem list"
                          }
                        ],
                        "code": {
                          "coding": [
                            {
                              "system": "urn:oid:2.16.840.1.113883.6.90",
                              "code": "R10.9"

                            },
                            {
                              "system": "urn:oid:2.16.840.1.113883.6.96",
                              "code": "271681002"

                            }
                          ],
                          "text": "Stomach ache"
                        }
                      },
                  }
               ]
            },
            {
            "label":"Diabetes",
            "uuid": "85126ce5-b0a7-4a54-86f4-d7b52426cc58",
            "actions":[
               {
                  "type":"create",
                  "description":"Diabetes Order Set from CDS Hooks",
                  "resource": {
                    "resourceType": "ServiceRequest",
                    "status": "draft",
                    "intent": "proposal",
                    "category": [
                      {
                      "coding": [
                        {
                          "system": "http://terminology.hl7.org/CodeSystem/medicationrequest-category",
                          "code": "outpatient",
                          "display": "Outpatient"
                        }]
                    }],
                    "code": {
                      "coding": [
                        {
                          "system": "urn:com.epic.cdshooks.action.code.system.orderset-item",
                          "code": "DIABETES"
                        }
                      ]
                    }
                  },
               },
            ]
         },
             {
                "label":"Test IP Medication Order",
                "uuid": "b1e0575b-2381-4625-b687-2def804d7c79",
                "actions":[
                   {
                      "type":"create",
                      "description":"Test Medication IP Order",
                      "resource": {
                        "resourceType": "MedicationRequest",
                        "status": "draft",
                        "intent": "proposal",
                        "category": [
                        {
                          "coding": [
                            {
                              "system": "http://terminology.hl7.org/CodeSystem/medicationrequest-category",
                              "code": "inpatient",
                              "display": "Inpatient"
                            }
                          ],
                          "text": "Inpatient"
                        }
                        ],
                        "medicationCodeableConcept": {
                          "coding": [
                            {
                              "system": "urn:oid:2.16.840.1.113883.6.69",
                              "code": "55111-682-01"
                            }
                          ],
                          "text": "Test Med Display name"
                        }
                      },
                   },
                ]
             },
             {
                "label":"Test Medication Order from Pref",
                "uuid": "5e0ce5e2-d33a-467c-bfc6-cde8d304e73d",
                "actions":[
                   {
                      "type":"create",
                      "description":"Test Medication Order from Pref",
                      "resource": {
                        "resourceType": "MedicationRequest",
                        "status": "draft",
                        "intent": "proposal",
                        "category": [
                        {
                          "coding": [
                            {
                              "system": "http://terminology.hl7.org/CodeSystem/medicationrequest-category",
                              "code": "inpatient",
                              "display": "Inpatient"
                            }
                          ],
                          "text": "Inpatient"
                        }
                        ],
                        "medicationCodeableConcept": {
                          "coding": [
                            {
                              "system": "urn:com.epic.cdshooks.action.code.system.preference-list-item",
                              "code": "BENAD25"
                            }
                          ],
                          "text": "Test Proc Display name"
                        }
                      },
                   },
                ]
             },
         {
            "label":"CBC",
            "uuid": "613b0192-4243-4384-8294-4316dfb726bb",
            "actions":[
               {
                  "type":"create",
                  "description":"CBC from CDS Hooks",
                  "resource": {
                    "resourceType": "ServiceRequest",
                    "status": "draft",
                    "intent": "proposal",
                    "category": [
                      {
                      "coding": [
                        {
                          "system": "http://terminology.hl7.org/CodeSystem/medicationrequest-category",
                          "code": "outpatient",
                          "display": "Outpatient"
                        }]
                    }],
                    "code": {
                      "coding": [
                        {
                          "system": "urn:com.epic.cdshooks.action.code.system.preference-list-item",
                          "code": "CBC_IP"
                        }
                      ],
                      "text": "Test Proc Display name"
                    }
                  },
               },
            ]}
        ]
      },
]
}
```

## Trusting CDS Clients

### JWT Tokens

To enable your CDS service to authenticate the identity of the CDS client, CDS hooks use digitally signed JSON web tokens (JWTs). Each time a client transmits a request to your service which requires authentication, the request must include an authorization header presenting the JWT as a “Bearer” token, which contains the following fields:

|           |                                                                                                     |
| --------- | --------------------------------------------------------------------------------------------------- |
| **Field** | **Description**                                                                                     |
| **alg**   | The cryptographic string used to sign this JWT. The default is RSA SHA-384.                         |
| **jku**   | The URL to the JWK Set containing the public key(s).                                                |
| **kid**   | The identifier of the key-pair used to sign this JWT.                                               |
| **typ**   | Fixed value: "JWT".                                                                                 |
| **aud**   | Your CDS service’s endpoint. This must be manually configured by the health system.                 |
| **exp**   | The expiration timer for the authentication JWT.                                                    |
| **iat**   | The issue time of the JWT.                                                                          |
| **iss**   | The URI of the JWT issuer, the FHIR endpoint of the organization. This must be manually configured. |
| **jti**   | A string value that uniquely identifies the JWT.                                                    |
| **nbf**   | Typically set to 5 minutes prior to the issue time of the JWT.                                      |
| **sub**   | CDS hooks client ID. This must be manually configured.                                              |

```
Header
{
  "alg": "RS384",
  "jku": "{{Base URL}}/api/epic/2019/Security/Open/PublicKeys/530013/530013",
  "kid": "d3bmo5HzW61TUgikHZH+A8Tx4UOXz2iOs4KvVU4eLY0=",
  "typ": "JWT"
}
Payload
{
  "aud": "https://example.com/savecdshooksrequest",
  "exp": 1708124873,
  "iat": 1708123973,
  "iss": "{{Base URL}}/api/FHIR/R4",
  "jti": "a42df6b7-2074-479a-b216-50eee1b09fb6",
  "nbf": 1708123673,
  "sub": "12345678-ce08-4ac7-ac0c-12345678"
}
```

### Install Considerations for the JWT Token

JWT authentication is configured in an External Endpoint Configuration record. The aud, iss, and sub claims are manually specified. These can be changed if your service requires a particular value.

- alg – This is typically RSA SHA-384
- aud – This is typically your CDS service’s endpoint
- iss – This is the FHIR server’s base url of the CDS Client
- sub – This is typically your CDS service’s client ID

To obtain the jku (JSON Web Key Set URL) from the installing organization, decode the JWT you receive in the “Authorization: Bearer” header, parse the jku claim from the JWT header, and verify the jku exists on your trusted allowlist of jku’s.

Make sure to not confuse the JWT you receive in the "Authorization: Bearer" header with the access token JWT you receive in the CDS Hooks request body. These two JWTs serve distinct purposes.

## Feedback

When configuring your CDS Hooks service during implementation, you can choose to receive feedback immediately or to receive it in a batch. If you use the batch format, the interval at which you receive feedback is defined through configuration at the implementing organization. By default, feedback is sent to your CDS Hooks service endpoint with “/feedback” appended.

A UUID must be sent in the CDS Hooks service response to uniquely identify cards or suggestions. If a UUID is not sent for these fields, the CDS Hooks client does not trigger feedback because the feedback can't be associated with a particular card or suggestion the CDS Hooks service provided.

Acknowledgement reasons can be configured within Epic or sent from your CDS service. Each option has varying Epic configuration steps and a different feedback message. For acknowledgement reasons built in Epic, the health system will need to add the reasons to the CDS build and the details will be sent in the extension component of the feedback message. If you are dynamically sending acknowledgement reasons, build needs to be completed by the health system to map the value being sent to an Epic record. In this case, the feedback message will utilize the reason field. The two Overridden Cards below show examples of the reason component and the extension field being used.

**Feedback Message Demonstrating Overridden Card with Reason**

```json
{"feedback": [{
            "card": "123456",
            "outcome": "overridden",
            "outcomeTimestamp": "2022-05-19T19:44:04Z",
            "overrideReasons": {
                "reason": {
                    "code": "contraindicated",
                    "display": "bad",
                    "system": "http: //example.org/cds-services/fhir/CodeSystem/override-reasons"
                },
                "userComment": "User Entered Free Text"}}]}
```

**Feedback Message Demonstrating Overridden Card with Extension**

```json
{"feedback": [{
            "card": "123456",
            "outcome": "overridden",
            "outcomeTimestamp": "2022-05-19T19:44:04Z",
            "overrideReasons": {
                  "extension": {
                       "com.epic.cdshooks.feedback.overrideReason.reasonCategory": "45",
                       "com.epic.cdshooks.feedback.overrideReason.reasonDisplay": "Does not meet criteria",
                       "com.epic.cdshooks.feedback.overrideReason.reasonTitle": "Does not meet criteria"
                },
                "userComment": "User Entered Free Text"}}]}
```

**Feedback Message Demonstrating Accepted Suggestion**

```json
{"feedback": [{
            "acceptedSuggestions": [{
                    "id": "replaceWithGUID"
                }
            ],
            "card": "123456",
            "outcome": "accepted",
            "outcomeTimestamp": "2022-05-19T19:48:34Z"}]}
```

## Medication References

Beginning in the February 2024 version of Epic, medications referenced from MedicationRequest resources in the draftOrders context as part of the order-select and order-sign hooks will be included as a contained resource within the draftOrders context. This eliminates the need for additional roundtrips to the server to obtain medication codes.

### Example Medication Reference

```json
"context": {
    "patientId": "eXoGxqgBaJuNkuahMYmiDhg3",
    "encounterId": "eAJ9U5Zv9Vzeg4lBWxmAQcItP6nlidE0QacJVtVudEQ43",
    "userId": "PractitionerRole/e-QokEGUJIzyynNdkCFrs9w3",
    "draftOrders": {
      "resourceType": "Bundle",
      "type": "collection",
      "entry": [
        {
          "resource": {
            "resourceType": "MedicationRequest",
            "id": "ez067mnwOAKP5z1.YJwRAsd9gCwdOzQ8wSrsM04QFoz882hxQZKBulF4smVj2SxHWfesiTZ1qsgBez8Rdeb2GpbWYuU.L0KkOqiZSgl2GBPFYUucdOKx53adK51FHbIL.9fyjChlCongwxq0kmbsAb63ITW14qpRUnm2l2PXADxvuolXYdkN80RBgyQwLK2O33",
            "status": "draft",
            "intent": "order",
            "category": [
              {
                "coding": [
                  {
                    "system": "http://terminology.hl7.org/CodeSystem/medicationrequest-category",
                    "code": "inpatient",
                    "display": "Inpatient"
                  }
                ],
                "text": "Inpatient"
              }
            ],
            "priority": "routine",
            "medicationReference": {
              "reference": "Medication/eVBXvKwrWZIkPmaGwY.s1hQ3",
              "display": "DEXTROMETHORPHAN HBR 15 MG/5ML PO SYRP"
            },
            "subject": {
              "reference": "Patient/eXoGxqgBaJuNkuahMYmiDhg3",
              "display": "Patient, Test"
            }
          }
        },
        {
          "resource": {
            "resourceType": "MedicationRequest",
            "id": "ez067mnwOAKP5z1.YJwRAsfY.5YNxZJJDzDQrJbuKBDbIp.vKaSouyn36H4Tc6-z2y9h2OU5FqxVeqUHFJRpGe4BxmHoRsVJB9GLVkHUmLPX-LyD02h3sLRMgK9uFNRU73KWgj0Tmeqi8Y.vVgy-6vka7hpwQHl1zLGD2OaLJ9rJfzfKH89zl25piLYkeGQMz3",
            "status": "draft",
            "intent": "order",
            "category": [
              {
                "coding": [
                  {
                    "system": "http://terminology.hl7.org/CodeSystem/medicationrequest-category",
                    "code": "inpatient",
                    "display": "Inpatient"
                  }
                ],
                "text": "Inpatient"
              }
            ],
            "priority": "routine",
            "medicationReference": {
              "reference": "Medication/emvpHliA4OaUxXJ4wp6N.Ig3",
              "display": "MERCAPTOPURINE 50 MG PO TABS"
            },
            "subject": {
              "reference": "Patient/eXoGxqgBaJuNkuahMYmiDhg3",
              "display": "Patient, Test"
            }
          }
        },
        {
          "resource": {
            "resourceType": "Medication",
            "id": "eVBXvKwrWZIkPmaGwY.s1hQ3",
            "identifier": [
              {
                "use": "usual",
                "system": "urn:oid:1.2.840.114350.1.13.861.1.7.2.698288",
                "value": "2356"
              }
            ],
            "code": {
              "coding": [
                {
                  "system": "urn:oid:2.16.840.1.113883.6.253",
                  "code": "6379"
                },
                {
                  "system": "urn:oid:2.16.840.1.113883.6.68",
                  "code": "43102030501215"
                },
                {
                  "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                  "code": "3289"
                },
                {
                  "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                  "code": "102490"
                },
                {
                  "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                  "code": "1090496"
                },
                {
                  "system": "urn:oid:2.16.840.1.113883.6.162",
                  "code": "01592"
                }
              ],
              "text": "dextromethorphan syrup 15 mg/5mL"
            },
            "form": {
              "coding": [
                {
                  "system": "urn:oid:1.2.840.114350.1.13.861.1.7.4.698288.310",
                  "code": "SYRP",
                  "display": "Syrup"
                }
              ],
              "text": "Syrup"
            },
            "ingredient": [
              {
                "itemCodeableConcept": {
                  "coding": [
                    {
                      "system": "urn:oid:2.16.840.1.113883.6.253",
                      "code": "6379"
                    },
                    {
                      "system": "urn:oid:2.16.840.1.113883.6.68",
                      "code": "43102030501215"
                    },
                    {
                      "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                      "code": "3289"
                    },
                    {
                      "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                      "code": "102490"
                    },
                    {
                      "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                      "code": "1090496"
                    },
                    {
                      "system": "urn:oid:2.16.840.1.113883.6.162",
                      "code": "01592"
                    }
                  ],
                  "text": "dextromethorphan syrup 15 mg/5mL"
                },
                "strength": {
                  "numerator": {
                    "value": 15,
                    "unit": "MG/5ML"
                  },
                  "denominator": {
                    "value": 15,
                    "unit": "MG/5ML"
                  }
                }
              }
            ]
          }
        },
        {
          "resource": {
            "resourceType": "Medication",
            "id": "emvpHliA4OaUxXJ4wp6N.Ig3",
            "identifier": [
              {
                "use": "usual",
                "system": "urn:oid:1.2.840.114350.1.13.861.1.7.2.698288",
                "value": "10531"
              }
            ],
            "code": {
              "coding": [
                {
                  "system": "urn:oid:2.16.840.1.113883.6.253",
                  "code": "28533"
                },
                {
                  "system": "urn:oid:2.16.840.1.113883.6.68",
                  "code": "21300040000305"
                },
                {
                  "system": "urn:oid:2.16.840.1.113883.6.162",
                  "code": "00597"
                },
                {
                  "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                  "code": "103"
                },
                {
                  "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                  "code": "197931"
                }
              ],
              "text": "mercaptopurine (PURINETHOL) tablet 50 mg"
            },
            "form": {
              "coding": [
                {
                  "system": "urn:oid:1.2.840.114350.1.13.861.1.7.4.698288.310",
                  "code": "TABS",
                  "display": "Tablet"
                }
              ],
              "text": "Tablet"
            },
            "ingredient": [
              {
                "itemCodeableConcept": {
                  "coding": [
                    {
                      "system": "urn:oid:2.16.840.1.113883.6.253",
                      "code": "28533"
                    },
                    {
                      "system": "urn:oid:2.16.840.1.113883.6.68",
                      "code": "21300040000305"
                    },
                    {
                      "system": "urn:oid:2.16.840.1.113883.6.162",
                      "code": "00597"
                    },
                    {
                      "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                      "code": "103"
                    },
                    {
                      "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                      "code": "197931"
                    }
                  ],
                  "text": "mercaptopurine (PURINETHOL) tablet 50 mg"
                },
                "strength": {
                  "numerator": {
                    "value": 50,
                    "unit": "MG",
                    "system": "http://unitsofmeasure.org",
                    "code": "mg"
                  },
                  "denominator": {
                    "value": 50,
                    "unit": "MG",
                    "system": "http://unitsofmeasure.org",
                    "code": "mg"
                  }
                }
              }
            ]
          }
        }
      ]
    }
  }
```

## Implementing CDS Hooks with an Epic Organization

When implementing your CDS service with an Epic organization, they will need certain pieces of information to complete their setup:

- Your CDS Hooks Client ID
  - When registering your app, the website creates an app record in the Epic database and assigns your app production and non-production client IDs.
  - The steps to register and receive your client IDs can be found in the App Request Process.
- Your CDS service’s endpoint
- Your service’s prefetch configuration, if applicable
- Expectations for JWT claims – aud, iss, and sub
- What workflow steps you expect to fire the hook
  - During implementation, the organization’s analysts will configure this to trigger during appropriate workflows and will determine where in workflows the service should be invoked.

There are also pieces of information that you will need to receive from the organization:

- The FHIR iss of the client
- The jku (JSON Web Key Set URL)

For more information, refer to our [Implementing a CDS Hooks App document](https://fhir.epic.com/Documentation?docId=implementing&section=implementingcdshooks).

## Gotchas

### Event Notification Streaming

CDS Hooks should be used only to trigger real-time, clinician-facing decision support. If your service never returns clinician-facing content, you should not use CDS Hooks.

If your use case requires notifications when an event occurs, you should use an event-based interface. For more information, refer to our [interfaces document](https://fhir.epic.com/Documentation?docid=interfaces). If your use case requires context synchronization, you should use [FHIRcast](https://open.epic.com/Prototype/Hyperdrive#FHIRcast).

### FHIR Version

When you register your CDS service with Epic’s authorization server infrastructure, the default FHIR version that you specify determines the FHIR version of resources in the CDS Hooks request, such as those in context or prefetch, as well as the specific fhirServer URL sent in the prefetch.

### Required OAuth 2.0 Scopes

- Context.draftOrders is only sent to a CDS service that’s authorized for the OAuth 2.0 scopes corresponding to the CDS Hooks-specific FHIR order resource (for example, MedicationRequest (Unsigned Order)).
- Similarly, a CDS service must be authorized for scopes corresponding to any resources requested as part of prefetch.

### Pre-Registration of Links and SMART Apps

As a security mechanism, SMART app link URLs returned within CDS Hooks cards must be pre-registered with the CDS client. SMART app URLs not pre-registered won't appear to the user.

### Endpoint URI Validation

For CDS Hooks to function appropriately, the URL used for your CDS Service must be defined in and exactly match an Endpoint URI defined on your application/client ID. If your CDS Service URL is not defined on your application's client ID, the hook will still trigger but it will be stripped of the information necessary for you to provide CDS.
