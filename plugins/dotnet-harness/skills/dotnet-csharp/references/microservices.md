# .NET Microservices Architecture Reference

Source: https://learn.microsoft.com/en-us/dotnet/architecture/microservices/

## Table of Contents
1. [Microservices vs Monolith](#vs-monolith)
2. [Service Design Principles](#design)
3. [Container & Docker](#docker)
4. [API Gateway Pattern](#gateway)
5. [Service Communication](#communication)
6. [Data Management](#data)
7. [Resilience Patterns](#resilience)
8. [Event-Driven Architecture](#events)
9. [Domain-Driven Design (DDD)](#ddd)
10. [CQRS & Event Sourcing](#cqrs)
11. [Security in Microservices](#security)
12. [Observability](#observability)
13. [Orchestration with Kubernetes](#k8s)

---

## 1. Microservices vs Monolith {#vs-monolith}

**Choose Microservices when:**
- Teams are large enough to own independent services (2-pizza rule)
- Different services have different scaling needs
- Need independent deployments and technology flexibility
- App has clear bounded contexts with low coupling

**Stick with Monolith when:**
- Small team or early-stage product
- Domain isn't yet well-understood
- Operational complexity of microservices outweighs benefits
- Strong data consistency requirements across the board

**Strangler Fig Pattern** — migrate from monolith gradually:
1. Route specific features to new microservice
2. Keep monolith running for everything else
3. Gradually migrate until monolith is replaced

---

## 2. Service Design Principles {#design}

- **Single Responsibility**: Each service owns one bounded context
- **Autonomous**: Can be deployed, scaled, and failed independently
- **Decentralized Data**: Each service owns its own database (no shared DB)
- **Smart endpoints, dumb pipes**: Business logic in services, not middleware
- **Design for failure**: Assume any downstream service can fail
- **Small surface area**: Minimize API surface; keep contracts stable

### Bounded Context Identification
```
eShopOnContainers example:
├── Catalog Service      — Products, inventory
├── Ordering Service     — Orders, order state machine
├── Basket Service       — Shopping cart (Redis-backed)
├── Identity Service     — Auth/users (IdentityServer)
├── Payment Service      — Payment processing
└── Notification Service — Email/push notifications
```

---

## 3. Container & Docker {#docker}

```dockerfile
# Optimized .NET microservice Dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# Restore separately for layer caching
COPY ["src/Catalog/Catalog.csproj", "src/Catalog/"]
RUN dotnet restore "src/Catalog/Catalog.csproj"

COPY . .
RUN dotnet publish "src/Catalog/Catalog.csproj" -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app
# Run as non-root for security
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser
COPY --from=build /app/publish .
EXPOSE 8080
ENTRYPOINT ["dotnet", "Catalog.dll"]
```

```yaml
# docker-compose.yml for local development
version: '3.9'
services:
  catalog-api:
    build: ./src/Catalog
    environment:
      - ASPNETCORE_ENVIRONMENT=Development
      - ConnectionStrings__Default=Server=sqlserver;...
    ports: ["5001:8080"]
    depends_on:
      sqlserver: { condition: service_healthy }
    
  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    environment:
      SA_PASSWORD: "Your_password123"
      ACCEPT_EULA: "Y"
    healthcheck:
      test: /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "Your_password123" -Q "SELECT 1"
      interval: 10s
      retries: 10
```

---

## 4. API Gateway Pattern {#gateway}

The API gateway is the single entry point for all clients. It handles:
- Request routing to downstream services
- Authentication/authorization
- Rate limiting and throttling
- Request/response transformation
- SSL termination
- Aggregation of multiple service calls

```csharp
// YARP (Yet Another Reverse Proxy) — Microsoft's recommended gateway
// nuget: Yarp.ReverseProxy

builder.Services.AddReverseProxy()
    .LoadFromConfig(builder.Configuration.GetSection("ReverseProxy"));

// appsettings.json
{
  "ReverseProxy": {
    "Routes": {
      "catalog-route": {
        "ClusterId": "catalog",
        "Match": { "Path": "/api/catalog/{**catch-all}" },
        "Transforms": [{ "PathRemovePrefix": "/api/catalog" }]
      }
    },
    "Clusters": {
      "catalog": {
        "Destinations": {
          "primary": { "Address": "http://catalog-api:8080" }
        }
      }
    }
  }
}
```

**Alternatives**: Azure API Management, AWS API Gateway, Kong, Nginx

**BFF (Backend for Frontend)**: Create separate gateways for web and mobile clients if their needs differ significantly.

---

## 5. Service Communication {#communication}

### Synchronous (HTTP/gRPC)
```csharp
// Typed HTTP client with resilience
builder.Services.AddHttpClient<ICatalogClient, CatalogClient>(client =>
{
    client.BaseAddress = new Uri("http://catalog-api");
    client.DefaultRequestHeaders.Add("Accept", "application/json");
})
.AddStandardResilienceHandler(); // Polly-based (retries, circuit breaker, timeout)

// Client implementation
public class CatalogClient(HttpClient http) : ICatalogClient
{
    public async Task<CatalogItem?> GetItemAsync(int id) =>
        await http.GetFromJsonAsync<CatalogItem>($"/api/catalog/items/{id}");
}
```

### gRPC for Internal Service-to-Service
```csharp
// More efficient than HTTP+JSON for internal communication
builder.Services.AddGrpcClient<Catalog.CatalogClient>(o =>
    o.Address = new Uri("http://catalog-api"));
```

### Service Discovery
```csharp
// With Aspire or Kubernetes DNS
// Services reference each other by name: http://catalog-api

// With Consul
builder.Services.AddServiceDiscovery();
builder.Services.ConfigureHttpClientDefaults(http =>
    http.AddServiceDiscovery());
```

---

## 6. Data Management {#data}

### Database Per Service
Each microservice has its own database — this is non-negotiable for true independence.

```
Catalog Service   → SQL Server (products, categories)
Basket Service    → Redis (ephemeral cart data)
Ordering Service  → SQL Server (orders, order items)
Identity Service  → SQL Server (users, roles)
```

### Entity Framework Core Setup
```csharp
// Each service has its own DbContext
public class CatalogContext(DbContextOptions<CatalogContext> options) : DbContext(options)
{
    public DbSet<CatalogItem> Items => Set<CatalogItem>();
    public DbSet<CatalogBrand> Brands => Set<CatalogBrand>();
    
    protected override void OnModelCreating(ModelBuilder b)
    {
        b.ApplyConfigurationsFromAssembly(typeof(CatalogContext).Assembly);
    }
}

// Registration
services.AddDbContext<CatalogContext>(opt =>
    opt.UseSqlServer(config.GetConnectionString("Default")));
```

### Eventual Consistency
When data must span services, use events rather than distributed transactions:
1. Service A completes its local transaction
2. Service A publishes a domain event
3. Service B handles the event and updates its own data
4. If B fails, retry from the message queue

**Never use distributed transactions (2PC)** — they break service autonomy.

---

## 7. Resilience Patterns {#resilience}

### Microsoft.Extensions.Http.Resilience (Polly v8)
```csharp
// Standard pipeline: retry + circuit breaker + timeout
services.AddHttpClient<ICatalogClient, CatalogClient>()
    .AddStandardResilienceHandler();

// Custom pipeline
services.AddHttpClient<ICatalogClient, CatalogClient>()
    .AddResilienceHandler("custom", pipeline =>
    {
        pipeline.AddRetry(new HttpRetryStrategyOptions
        {
            MaxRetryAttempts = 3,
            Delay = TimeSpan.FromSeconds(1),
            BackoffType = DelayBackoffType.Exponential,
            ShouldHandle = new PredicateBuilder<HttpResponseMessage>()
                .Handle<HttpRequestException>()
                .HandleResult(r => r.StatusCode >= HttpStatusCode.InternalServerError)
        });
        
        pipeline.AddCircuitBreaker(new HttpCircuitBreakerStrategyOptions
        {
            SamplingDuration = TimeSpan.FromSeconds(30),
            FailureRatio = 0.5,
            MinimumThroughput = 10,
            BreakDuration = TimeSpan.FromSeconds(60)
        });
        
        pipeline.AddTimeout(TimeSpan.FromSeconds(10));
    });
```

### Health Checks
```csharp
builder.Services.AddHealthChecks()
    .AddSqlServer(connStr)
    .AddRedis(redisConnStr)
    .AddUrlGroup(new Uri("http://external-service/health"), "external");

app.MapHealthChecks("/health/ready", new HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("ready")
});
app.MapHealthChecks("/health/live", new HealthCheckOptions
{
    Predicate = _ => false  // liveness: just 200 if process is up
});
```

### Timeout & Fallback
```csharp
// Always set timeouts on outbound calls
client.Timeout = TimeSpan.FromSeconds(5);

// Provide degraded/fallback responses
public async Task<CatalogItem?> GetItemWithFallbackAsync(int id)
{
    try { return await _client.GetItemAsync(id); }
    catch (Exception) { return _cache.Get(id); }  // stale data > no data
}
```

---

## 8. Event-Driven Architecture {#events}

### Integration Events (between services)
```csharp
// Event definition (shared contract)
public record OrderPlacedIntegrationEvent(
    int OrderId,
    string UserId,
    IReadOnlyList<OrderItem> Items,
    DateTime PlacedAt
);

// Publisher (Ordering Service)
public class OrderService(IEventBus eventBus)
{
    public async Task PlaceOrderAsync(PlaceOrderCommand cmd)
    {
        // 1. Save order locally
        var order = await SaveOrderAsync(cmd);
        
        // 2. Publish event (use Outbox pattern for atomicity)
        await eventBus.PublishAsync(new OrderPlacedIntegrationEvent(
            order.Id, cmd.UserId, cmd.Items, DateTime.UtcNow));
    }
}

// Subscriber (Catalog Service)
public class OrderPlacedHandler : IIntegrationEventHandler<OrderPlacedIntegrationEvent>
{
    public async Task HandleAsync(OrderPlacedIntegrationEvent @event)
    {
        // Decrease stock for ordered items
        foreach (var item in @event.Items)
            await _catalog.DecrementStockAsync(item.ProductId, item.Quantity);
    }
}
```

### Message Brokers
| Broker | Best For |
|--------|---------|
| **RabbitMQ** | Simple pub/sub, on-premises, low latency |
| **Azure Service Bus** | Azure-native, enterprise features, dead-lettering |
| **Apache Kafka** | High-throughput event streaming, event sourcing |
| **AWS SQS/SNS** | AWS-native serverless messaging |

```csharp
// MassTransit — abstraction over RabbitMQ, Azure Service Bus, etc.
builder.Services.AddMassTransit(x =>
{
    x.AddConsumer<OrderPlacedHandler>();
    x.UsingRabbitMq((ctx, cfg) =>
    {
        cfg.Host("rabbitmq://localhost");
        cfg.ConfigureEndpoints(ctx);
    });
});
```

### Outbox Pattern (Reliable Publishing)
```csharp
// Atomically save entity + event in same DB transaction
public async Task PlaceOrderAsync(PlaceOrderCommand cmd)
{
    await using var tx = await _db.Database.BeginTransactionAsync();
    
    var order = new Order(cmd);
    _db.Orders.Add(order);
    
    // Outbox: store event in same transaction
    _db.OutboxMessages.Add(new OutboxMessage
    {
        EventType = nameof(OrderPlacedIntegrationEvent),
        Payload = JsonSerializer.Serialize(new OrderPlacedIntegrationEvent(...)),
        CreatedAt = DateTime.UtcNow
    });
    
    await _db.SaveChangesAsync();
    await tx.CommitAsync();
    // Background job polls OutboxMessages and publishes to broker
}
```

---

## 9. Domain-Driven Design (DDD) {#ddd}

### Tactical Patterns
```csharp
// Aggregate Root — owns consistency boundary
public class Order : Entity, IAggregateRoot
{
    private readonly List<OrderItem> _items = new();
    public IReadOnlyList<OrderItem> Items => _items.AsReadOnly();
    public OrderStatus Status { get; private set; }
    
    private Order() {} // EF Core
    
    public static Order Create(string userId)
    {
        var order = new Order { UserId = userId, Status = OrderStatus.Draft };
        order.AddDomainEvent(new OrderCreatedDomainEvent(order));
        return order;
    }
    
    public void AddItem(int productId, int quantity, decimal unitPrice)
    {
        // Business rule enforcement inside the aggregate
        if (Status != OrderStatus.Draft) throw new InvalidOperationException();
        _items.Add(new OrderItem(productId, quantity, unitPrice));
    }
    
    public void PlaceOrder()
    {
        if (!_items.Any()) throw new DomainException("Cannot place empty order");
        Status = OrderStatus.Placed;
        AddDomainEvent(new OrderPlacedDomainEvent(this));
    }
}

// Value Object — equality by value, immutable
public record Money(decimal Amount, string Currency)
{
    public Money Add(Money other)
    {
        if (Currency != other.Currency) throw new InvalidOperationException();
        return this with { Amount = Amount + other.Amount };
    }
}

// Domain Event
public record OrderPlacedDomainEvent(Order Order) : IDomainEvent;
```

### Repository Pattern
```csharp
public interface IOrderRepository
{
    Task<Order?> FindByIdAsync(int id, CancellationToken ct = default);
    Task<IEnumerable<Order>> FindByUserIdAsync(string userId);
    void Add(Order order);
    void Update(Order order);
    Task<int> SaveChangesAsync(CancellationToken ct = default);
}
```

---

## 10. CQRS & Event Sourcing {#cqrs}

### CQRS with MediatR
```csharp
// Commands — change state
public record PlaceOrderCommand(string UserId, List<OrderItemDto> Items) : IRequest<int>;

public class PlaceOrderHandler(IOrderRepository repo) : IRequestHandler<PlaceOrderCommand, int>
{
    public async Task<int> Handle(PlaceOrderCommand cmd, CancellationToken ct)
    {
        var order = Order.Create(cmd.UserId);
        foreach (var item in cmd.Items)
            order.AddItem(item.ProductId, item.Quantity, item.UnitPrice);
        order.PlaceOrder();
        
        repo.Add(order);
        await repo.SaveChangesAsync(ct);
        return order.Id;
    }
}

// Queries — read state (can hit read replica)
public record GetOrderQuery(int OrderId) : IRequest<OrderDto?>;

public class GetOrderHandler(IReadDbContext db) : IRequestHandler<GetOrderQuery, OrderDto?>
{
    public async Task<OrderDto?> Handle(GetOrderQuery q, CancellationToken ct) =>
        await db.Orders.AsNoTracking()
            .Where(o => o.Id == q.OrderId)
            .Select(o => new OrderDto(o.Id, o.Status, o.Items.Count))
            .FirstOrDefaultAsync(ct);
}

// MediatR setup
services.AddMediatR(cfg => cfg.RegisterServicesFromAssemblyContaining<Program>());

// Endpoint usage
app.MapPost("/orders", async (PlaceOrderCommand cmd, IMediator mediator) =>
{
    var orderId = await mediator.Send(cmd);
    return Results.Created($"/orders/{orderId}", new { orderId });
});
```

---

## 11. Security in Microservices {#security}

- **Centralize authentication**: Use a dedicated Identity Service (IdentityServer/Duende, Azure AD, Keycloak)
- **JWT bearer tokens**: Services validate tokens independently (no central session store)
- **Service-to-service auth**: Use mutual TLS (mTLS) or client credentials grant
- **Network policies**: Use Kubernetes NetworkPolicy or service mesh (Istio/Linkerd) to restrict inter-service traffic
- **Secrets management**: Use Azure Key Vault, AWS Secrets Manager, or Kubernetes Secrets (encrypted at rest)

```csharp
// Each service validates JWTs independently
services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(opt =>
    {
        opt.Authority = "https://identity-service";  // OIDC discovery
        opt.Audience = "catalog-api";
        opt.RequireHttpsMetadata = true;
    });
```

---

## 12. Observability {#observability}

```csharp
// OpenTelemetry (distributed tracing, metrics, logs)
builder.Services.AddOpenTelemetry()
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddEntityFrameworkCoreInstrumentation()
        .AddOtlpExporter(o => o.Endpoint = new Uri("http://otel-collector:4317")))
    .WithMetrics(m => m
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddPrometheusExporter());

// Structured logging with Serilog
builder.Host.UseSerilog((ctx, cfg) =>
    cfg.ReadFrom.Configuration(ctx.Configuration)
       .Enrich.WithProperty("Service", "CatalogApi")
       .WriteTo.Console(new JsonFormatter())
       .WriteTo.Seq("http://seq:5341"));
```

**Observability Stack:**
- **Tracing**: Jaeger, Zipkin, Azure Monitor, Datadog
- **Metrics**: Prometheus + Grafana
- **Logging**: ELK Stack, Seq, Azure Monitor Logs
- **All-in-one**: Aspire Dashboard (development), Datadog, Dynatrace

---

## 13. Orchestration with Kubernetes {#k8s}

```yaml
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalog-api
spec:
  replicas: 3
  selector:
    matchLabels: { app: catalog-api }
  template:
    metadata:
      labels: { app: catalog-api }
    spec:
      containers:
        - name: catalog-api
          image: myregistry/catalog-api:latest
          ports: [{ containerPort: 8080 }]
          env:
            - name: ASPNETCORE_ENVIRONMENT
              value: Production
            - name: ConnectionStrings__Default
              valueFrom:
                secretKeyRef: { name: catalog-secrets, key: connection-string }
          resources:
            requests: { memory: "128Mi", cpu: "100m" }
            limits: { memory: "256Mi", cpu: "500m" }
          readinessProbe:
            httpGet: { path: /health/ready, port: 8080 }
            initialDelaySeconds: 10
          livenessProbe:
            httpGet: { path: /health/live, port: 8080 }
            periodSeconds: 30

---
# Service (ClusterIP for internal, LoadBalancer for external)
apiVersion: v1
kind: Service
metadata:
  name: catalog-api
spec:
  selector: { app: catalog-api }
  ports: [{ port: 80, targetPort: 8080 }]
```

### .NET Aspire (Local Development Orchestration)
```csharp
// AppHost/Program.cs — Aspire orchestrator
var builder = DistributedApplication.CreateBuilder(args);

var sqlServer = builder.AddSqlServer("sqlserver")
    .AddDatabase("catalogdb");

var redis = builder.AddRedis("redis");

var catalog = builder.AddProject<Projects.Catalog_Api>("catalog-api")
    .WithReference(sqlServer)
    .WithReference(redis);

builder.AddProject<Projects.ApiGateway>("gateway")
    .WithReference(catalog);

builder.Build().Run();
```

Aspire provides: service discovery, health dashboard, distributed tracing, and simplified local development without Docker Compose.
