# Architecture — ShopAssist E-Commerce Agent

## High-Level Architecture

```mermaid
flowchart LR
    subgraph Client["Client Layer"]
        User[👤 Customer]
        CLI[CLI / API / Web]
    end

    subgraph Agent["Agent Layer (Strands SDK)"]
        SA[Strands Agent]
        SP[System Prompt]
        TL[Tool Registry]
    end

    subgraph Bedrock["Amazon Bedrock"]
        Model[Claude Sonnet 4]
        RA[Responses API]
    end

    subgraph Gateway["AgentCore Gateway"]
        GW[MCP Endpoint]
        Auth[Auth Layer]
        Search[Semantic Tool Search]
    end

    subgraph Lambda["AWS Lambda"]
        L1[Products Handler]
        L2[Cart Handler]
        L3[Orders Handler]
    end

    subgraph Data["Data Layer"]
        DDB1[(Products Table)]
        DDB2[(Carts Table)]
        DDB3[(Orders Table)]
    end

    User --> CLI --> SA
    SA --> SP
    SA --> TL
    SA --> Model
    Model --> GW
    GW --> Auth
    GW --> Search
    GW --> L1 & L2 & L3
    L1 --> DDB1
    L2 --> DDB2
    L3 --> DDB3
```

## Client-Side vs Server-Side Tool Execution

### Client-Side Execution Flow

```mermaid
sequenceDiagram
    participant U as User
    participant A as Strands Agent
    participant B as Bedrock (Claude)
    participant M as MCP Client
    participant G as AgentCore Gateway
    participant L as Lambda

    U->>A: "Find wireless headphones under $100"
    A->>B: messages + tools (from Gateway)
    B-->>A: tool_use: search_products(query="wireless headphones", max_price=100)
    A->>M: call_tool("search_products", {...})
    M->>G: MCP invokeTool (Streamable HTTP)
    G->>L: Invoke Lambda
    L-->>G: {products: [...]}
    G-->>M: tool result
    M-->>A: tool result
    A->>B: messages + tool_result
    B-->>A: "Here are 3 great options..."
    A-->>U: Final response with product list
```

### Server-Side Execution Flow

```mermaid
sequenceDiagram
    participant U as User
    participant C as Client Code
    participant R as Bedrock Responses API
    participant B as Bedrock (Claude)
    participant G as AgentCore Gateway
    participant L as Lambda

    U->>C: "Find wireless headphones under $100"
    C->>R: create_response(input, tools=[mcpServerConnector], toolExecution=enabled)

    Note over R,L: Everything below happens server-side in a single API call

    R->>G: Discover tools (listTools)
    G-->>R: Available tools list
    R->>B: messages + discovered tools
    B-->>R: tool_use: search_products(...)
    R->>G: Execute tool (invokeTool)
    G->>L: Invoke Lambda
    L-->>G: {products: [...]}
    G-->>R: tool result
    R->>B: messages + tool_result
    B-->>R: "Here are 3 great options..."

    R-->>C: Final response (streamed)
    C-->>U: Display response
```

## AgentCore Gateway Architecture

```mermaid
graph TB
    subgraph "Inbound"
        Agent[Agent / MCP Client]
        Agent -->|Streamable HTTP| EP[Gateway MCP Endpoint]
    end

    subgraph "AgentCore Gateway"
        EP --> AuthZ[Inbound Auth<br/>IAM / OAuth / JWT]
        AuthZ --> Router[Tool Router]
        Router --> TS[Semantic Tool Search<br/>Vector Embeddings]
        Router --> T1[Target: Products Lambda]
        Router --> T2[Target: Cart Lambda]
        Router --> T3[Target: Orders Lambda]
    end

    subgraph "Outbound"
        T1 -->|IAM Role| L1[Lambda: Products]
        T2 -->|IAM Role| L2[Lambda: Cart]
        T3 -->|IAM Role| L3[Lambda: Orders]
    end

    subgraph "Credential Management"
        CP[AgentCore Identity<br/>Credential Provider]
        CP -.->|OAuth tokens<br/>API keys| Router
    end

    style AuthZ fill:#ff6b6b,color:#fff
    style TS fill:#4ecdc4,color:#000
    style CP fill:#45b7d1,color:#000
```

## Data Model

### Products Table
| Field | Type | Description |
|-------|------|-------------|
| id | S (PK) | Product ID (e.g., ELEC-001) |
| category | S (GSI) | Product category |
| name | S | Product name |
| description | S | Full description |
| price | N | Price in USD |
| rating | N | Average rating (1-5) |
| reviews | N | Number of reviews |
| in_stock | BOOL | Availability |

### Carts Table
| Field | Type | Description |
|-------|------|-------------|
| customer_id | S (PK) | Customer ID |
| items | L | List of {product_id, quantity, price} |
| applied_coupon | S | Active coupon code |
| ttl | N | Auto-expire after 24h |

### Orders Table
| Field | Type | Description |
|-------|------|-------------|
| order_id | S (PK) | Order ID |
| customer_id | S (GSI) | Customer ID |
| items | L | Ordered items |
| total | N | Order total |
| status | S | confirmed/shipped/delivered/return_requested |
| created_at | S | ISO timestamp |

## Key Design Decisions

1. **Local-first**: Demo works without AWS deployment using in-memory mock data
2. **Dual-mode**: Supports both client-side and server-side tool execution to demonstrate the difference
3. **MCP-native**: All tools exposed via MCP protocol through AgentCore Gateway
4. **Stateless Lambda**: Cart/order state in DynamoDB, Lambda functions are stateless
5. **Semantic search ready**: Gateway's built-in semantic tool search works with large tool collections (100+)
