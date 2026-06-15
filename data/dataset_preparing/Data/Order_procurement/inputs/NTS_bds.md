**Business Specification (For OCEL Generator và Process Analysis**)

# **1\. Business Context**

## **Process Scope**

Cross-functional Order Management and Order Fulfillment Process

## **Organization**

Nam Truong Son Hanoi Corporation (ICT Distributor)

## **Research Scope**

Phân tích và cải thiện:

* Inter-departmental coordination  
* Operational document governance  
* CRM-based document monitoring

Không bao gồm:

* Marketing  
* Deal Registration  
* Opportunity Development  
* Tendering Activities  
* After-sales Support

**System Context**

**CRM Adoption Stage**: Early Adoption Phase

**Observation Period:**

January 2026 – April 2026

**Business Environment:**

The CRM platform has recently been deployed and is currently used by multiple departments for cross-functional order management activities. However, process standardization, governance mechanisms, and document monitoring capabilities are still under development.

External communication with vendors and customers continues through email, messaging platforms, and external collaboration tools, resulting in partial information fragmentation.

# **2\. Process Participants**

| Role | Responsibility |
| ----- | ----- |
| Sales | Receive customer requirements, initiate order |
| PM | Coordinate process and vendors |
| Technical | Validate technical requirements and BOM |
| Accounting | Financial and document validation |
| Logistics | Delivery and shipment management |
| Admin | Inventory receiving and warehouse confirmation |
| Vendor | Provide quotation, licensing, shipment information |

# **3\. Business Objects (Documents)**

## **Purchase Order**

Purpose: Customer purchasing request.

Owner: Sales

Used by: PM, Accounting

Lifecycle:

Created  
→ Reviewed  
→ Validated  
→ Approved  
→ Ordered  
→ Closed

## **Vendor Quote Request**

Purpose: Quotation request sent to vendor.

Owner: PM

Used by: Vendor

Lifecycle:

Created

→ Sent

→ Completed

## 

## **Vendor Quotation**

Purpose: Official quotation from vendor.

Owner: Vendor

Used by: PM, Technical, Accounting

Lifecycle:

Requested  
→ Received  
→ Reviewed  
→ Approved

## **BOM Configuration**

Purpose: Technical validation document.

Owner: Technical

Used by: PM

Lifecycle:

Draft  
→ Validated  
→ Approved

## **Licensing Document**

Purpose: Software licensing confirmation.

Owner: Vendor

Used by: PM, Technical

Lifecycle:

Received

→ Checked

→ Approved

## **Shipment Document**

Purpose: Shipment information.

Owner: Vendor

Used by: PM, Logistics

Lifecycle:

Created

→ Validated

→ Delivered

→ Verified

## **Inventory Record**

Purpose: Goods receiving confirmation.

Owner: Admin

Used by: Accounting

Lifecycle:

Created  
→ Updated  
→ Archived

# **4\. Activities (Based on BPMN)**

| Sales Confirm Customer Order Submit Purchase Order  | PM Review Order Information Request Vendor Quote Coordinate Vendor Communication Create Vendor Order Track Delivery Progress | Technical Validate BOM Verify Product Configuration Verify Licensing Information Verify Shipment Information  |
| :---- | :---- | :---- |
| **Accounting** Validate Quotation Validate Tax Information Approve Financial Documents Verify Goods Receipt  | **Logistics** Process Shipment Estimate Delivery Timeline  | **Admin** Receive Goods Stock In Inventory |

# **Activity–Document Mapping** 

| Activity | Main Document | Action |
| ----- | ----- | ----- |
| Confirm Customer Order | Purchase Order | Create |
| Submit Purchase Order | Purchase Order | Submit |
| Review Order Information | Purchase Order | Review |
| Request Vendor Quote | Vendor Quote Request | Create |
| Coordinate Vendor Communication | Vendor Quotation | Update |
| Validate BOM | BOM Configuration | Validate |
| Verify Product Configuration | BOM Configuration | Verify |
| Validate Quotation | Vendor Quotation | Validate |
| Validate Tax Information | Purchase Order | Validate |
| Approve Financial Documents | Purchase Order | Approve |
| Create Vendor Order | Purchase Order | Update |
| Verify Licensing Information | Licensing Document | Validate |
| Verify Shipment Information | Shipment Document | Validate |
| Process Shipment | Shipment Document | Update |
| Estimate Delivery Timeline | Shipment Document | Update |
| Verify Goods Receipt | Shipment Document | Verify |
| Receive Goods | Inventory Record | Create |
| Stock In Inventory | Inventory Record | Update |

# **5\. Handover Matrix**

Đây chính là governance layer sau này.

| From | To | Object |
| ----- | ----- | ----- |
| Sales | PM | Purchase Order |
| PM | Vendor | Quote Request |
| Vendor | PM | Vendor Quotation |
| PM | Technical | BOM |
| Technical | PM | Validated BOM |
| PM | Accounting | Quotation Package |
| Accounting | PM | Approved Package |
| PM | Logistics | Shipment Package |
| Logistics | Accounting | Receiving Documents |
| Accounting | Admin | Goods Confirmation |

## Governance Rules

# GR-01: Vendor Quotation must be received before BOM validation.

# Receive Vendor Quotation → Validate BOM

# GR-02: Validated BOM is required before Vendor Order creation.

# Validate BOM → Create Vendor Order

# GR-03: Tax validation is required before Vendor Order creation.

# Validate Tax Information → Create Vendor Order

# GR-04: Licensing verification must be completed before shipment processing.

# Verify Licensing Information → Process Shipment

# GR-05: Shipment documents must be validated before goods receipt.

# Verify Shipment Information → Receive Goods

# GR-06: Inventory can only be updated after goods receipt verification.

# Verify Goods Receipt → Stock In Inventory

# **6\. Current-State Vulnerabilities**

*(inject into synthetic event log)*

The following vulnerabilities were identified through BPMN analysis, internal process documentation, and observations of CRM-supported operations.

V1 Missing Information

Description:

Required information is incomplete when documents are transferred between departments.

Example:

Incomplete customer requirements, missing product specifications, incomplete vendor responses.

Source:

Internal PM Report.

\---

V2 Communication Fragmentation

Description:

Business communication occurs through multiple disconnected channels.

Example:

Zalo, WhatsApp, Email, Phone Calls.

Source:

Internal PM Report.

\---

V3 Delayed Status Update

Description:

Process participants fail to update document or activity status in a timely manner.

Example:

Shipment status updates not reflected immediately in CRM.

Source:

Internal PM Report.

\---

V4 BOM Rework

Description:

Technical specifications require repeated corrections due to incomplete or inconsistent information.

Source:

Internal PM Report.

\---

V5 Product Naming Inconsistency

Description:

Different departments or vendors use inconsistent naming conventions for identical products.

Source:

Internal PM Report.

\---

V6 Cross-department Synchronization Issue

Description:

Information maintained by different departments becomes inconsistent during process execution.

Example:

PM and Technical maintain different document versions.

Source:

Internal PM Report.

# **6.1. Vulnerability Injection Rules**

# To simulate realistic operational conditions during the early CRM adoption stage, synthetic event logs should reflect the identified vulnerabilities naturally through channel usage, time gaps between activities, rework loops, and relationship patterns rather than heavy use of explicit flags.

# **Observation Period:**

# January 2026 – April 2026

# **Approximate distribution (reflected in generated log):**

* # Communication Fragmentation (Zalo/WhatsApp/Phone): 20–25% of events

* # Delayed Status Updates: 15–20% of cases (visible via time gaps)

* # Missing Information & Rework: 10–15% of cases

* # Cross-department Synchronization Issues: 10–15% of cases

* # BOM Rework: 5–10% of cases

* # Product Naming Inconsistency: 5–8% of cases

  # 

# The objective is not to create abnormal process behavior but to realistically represent operational challenges observed during the current-state assessment.

# **7\. Root Cause Mapping**

| Root Cause 1 Insufficient Inter-departmental Governance Manifested by: Communication Fragmentation Delayed Updates Unclear Responsibilities Repeated Validation Activities Inconsistent Handover Practices  | Root Cause 2 Limited Operational Document Traceability Manifested by: Missing Information Document Mismatch Ownership Uncertainty Incomplete Document History Limited Process Visibility |
| :---- | :---- |

# **8\. Expected Monitoring Indicators (Dashboard)**

### **Governance Indicators**

* Document Owner  
* Current Responsible Department  
* Pending Validation  
* Escalated Cases  
* Governance Rule Violations

### **Monitoring Indicators**

* Document Status  
* Lead Time  
* Waiting Time  
* Rework Count  
* Delay Count  
* Handover Count  
* Traceability Completeness

# **9\. OCEL Generator Mapping**

### **Objects**

PurchaseOrder  
VendorQuotation  
BOM  
LicensingDocument  
ShipmentDocument  
InventoryRecord

### **Object Types**

Document  
Department  
Vendor

### **Events**

ConfirmCustomerOrder  
SubmitPurchaseOrder  
ReviewOrderInformation  
RequestVendorQuote  
ReceiveVendorQuotation  
ValidateBOM  
VerifyProductConfiguration  
ValidateQuotation  
ValidateTaxInformation  
ApproveFinancialDocuments  
CreateVendorOrder  
VerifyLicensingInformation  
VerifyShipmentInformation  
ProcessShipment  
EstimateDeliveryTimeline  
VerifyGoodsReceipt  
ReceiveGoods  
StockInInventory  
CloseOrder

### **Event Attributes**

Timestamp  
Actor  
Department (as relationship preferred)  
DocumentID  
Status  
Channel  
(DelayFlag / ReworkFlag used sparingly only for clear analysis support, not as primary alert mechanism)

**Key Relationships**:

performedBy, actor

handoverTo, recipient, notified, coordinator

Department objects are modeled separately (DEPT-SALES, DEPT-PM, etc.) to enable clear analysis of inter-departmental handovers and governance.

