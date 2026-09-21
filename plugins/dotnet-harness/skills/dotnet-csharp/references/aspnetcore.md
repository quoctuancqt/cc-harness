# ASP.NET Core Reference

Source: https://learn.microsoft.com/en-gb/aspnet/core/overview?view=aspnetcore-8.0

## Table of Contents
1. [Project Setup](#setup)
2. [Minimal APIs](#minimal-apis)
3. [MVC & Razor Pages](#mvc)
4. [Dependency Injection](#di)
5. [Middleware Pipeline](#middleware)
6. [Configuration](#configuration)
7. [Authentication & Authorization](#auth)
8. [Blazor](#blazor)
9. [SignalR & gRPC](#realtime)
10. [Testing](#testing)
11. [Deployment](#deployment)

---

## 1. Project Setup {#setup}

```xml
<!-- .csproj -->
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
</Project>
```

```csharp
// Program.cs — Minimal API style (preferred for new projects)
var builder = WebApplication.CreateBuilder(args);

// Add services
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
builder.Services.AddScoped<IUserService, UserService>();

var app = builder.Build();

// Configure pipeline
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();
app.UseAuthentication();
app.UseAuthorization();

// Map endpoints
app.MapGet("/health", () => Results.Ok(new { Status = "healthy" }));

app.Run();
```

---

## 2. Minimal APIs {#minimal-apis}

```csharp
// Route groups (organize related endpoints)
var users = app.MapGroup("/api/users").RequireAuthorization();

users.MapGet("/", async (IUserService svc) =>
    Results.Ok(await svc.GetAllAsync()));

users.MapGet("/{id:int}", async (int id, IUserService svc) =>
    await svc.GetByIdAsync(id) is { } user
        ? Results.Ok(user)
        : Results.NotFound());

users.MapPost("/", async (CreateUserRequest req, IUserService svc) =>
{
    var user = await svc.CreateAsync(req);
    return Results.CreatedAtRoute("GetUser", new { id = user.Id }, user);
}).WithName("CreateUser");

users.MapPut("/{id:int}", async (int id, UpdateUserRequest req, IUserService svc) =>
{
    if (!await svc.UpdateAsync(id, req)) return Results.NotFound();
    return Results.NoContent();
});

users.MapDelete("/{id:int}", async (int id, IUserService svc) =>
{
    if (!await svc.DeleteAsync(id)) return Results.NotFound();
    return Results.NoContent();
});
```

### Request/Response Handling
```csharp
// Model binding — from route, query, body, header
app.MapGet("/search", (string? q, int page = 1, int pageSize = 20) => 
    Results.Ok(new { q, page, pageSize }));

// File upload
app.MapPost("/upload", async (IFormFile file) =>
{
    await using var stream = file.OpenReadStream();
    // process...
    return Results.Ok(new { file.FileName, file.Length });
});

// Results helpers
Results.Ok(value)           // 200
Results.Created(uri, value) // 201
Results.NoContent()         // 204
Results.NotFound()          // 404
Results.BadRequest(errors)  // 400
Results.Unauthorized()      // 401
Results.Forbid()            // 403
Results.Problem(detail)     // RFC 7807 problem details

// Typed results (better for OpenAPI/testing)
TypedResults.Ok(value)
TypedResults.NotFound()
```

### Validation
```csharp
// Use FluentValidation
builder.Services.AddValidatorsFromAssemblyContaining<Program>();

app.MapPost("/users", async (CreateUserRequest req, IValidator<CreateUserRequest> validator) =>
{
    var result = await validator.ValidateAsync(req);
    if (!result.IsValid)
        return Results.ValidationProblem(result.ToDictionary());
    // ...
});
```

---

## 3. MVC & Razor Pages {#mvc}

```csharp
// MVC setup
builder.Services.AddControllersWithViews();
app.MapControllerRoute("default", "{controller=Home}/{action=Index}/{id?}");

// Controller
[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    private readonly IUserService _service;
    
    public UsersController(IUserService service) => _service = service;
    
    [HttpGet("{id}")]
    [ProducesResponseType(typeof(UserDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Get(int id)
    {
        var user = await _service.GetByIdAsync(id);
        return user is null ? NotFound() : Ok(user);
    }
    
    [HttpPost]
    public async Task<IActionResult> Create(CreateUserRequest req)
    {
        if (!ModelState.IsValid) return BadRequest(ModelState);
        var user = await _service.CreateAsync(req);
        return CreatedAtAction(nameof(Get), new { id = user.Id }, user);
    }
}
```

### Razor Pages
```csharp
// Pages/Users/Index.cshtml.cs
public class IndexModel : PageModel
{
    private readonly IUserService _service;
    public IEnumerable<UserDto> Users { get; private set; } = [];
    
    public IndexModel(IUserService service) => _service = service;
    
    public async Task OnGetAsync() =>
        Users = await _service.GetAllAsync();
    
    [BindProperty]
    public CreateUserRequest Input { get; set; } = new();
    
    public async Task<IActionResult> OnPostAsync()
    {
        if (!ModelState.IsValid) return Page();
        await _service.CreateAsync(Input);
        return RedirectToPage();
    }
}
```

---

## 4. Dependency Injection {#di}

```csharp
// Service lifetimes
services.AddSingleton<IMemoryCache, MemoryCache>();    // One instance per app
services.AddScoped<IUserService, UserService>();        // One per HTTP request
services.AddTransient<IEmailSender, SmtpEmailSender>(); // New instance each time

// Keyed services (ASP.NET Core 8+)
services.AddKeyedSingleton<ICache, RedisCache>("redis");
services.AddKeyedSingleton<ICache, MemoryCache>("memory");

// Injection
public class MyService([FromKeyedServices("redis")] ICache cache) { }

// Factory pattern
services.AddTransient<IDbConnection>(_ =>
    new SqlConnection(config.GetConnectionString("Default")));

// Options
services.Configure<JwtOptions>(config.GetSection("Jwt"));
services.AddOptions<SmtpOptions>()
    .Bind(config.GetSection("Smtp"))
    .ValidateDataAnnotations()
    .ValidateOnStart();
```

---

## 5. Middleware Pipeline {#middleware}

```csharp
// Order matters! Typical order:
app.UseExceptionHandler("/error");
app.UseHsts();
app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseRouting();
app.UseCors("MyPolicy");
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();

// Custom middleware
public class RequestTimingMiddleware(RequestDelegate next, ILogger<RequestTimingMiddleware> logger)
{
    public async Task InvokeAsync(HttpContext context)
    {
        var sw = Stopwatch.StartNew();
        await next(context);
        sw.Stop();
        logger.LogInformation("{Method} {Path} took {ElapsedMs}ms",
            context.Request.Method, context.Request.Path, sw.ElapsedMilliseconds);
    }
}

// Registration
app.UseMiddleware<RequestTimingMiddleware>();

// Or as endpoint filter (Minimal APIs)
app.MapGet("/", () => "Hello")
   .AddEndpointFilter(async (ctx, next) =>
   {
       // before
       var result = await next(ctx);
       // after
       return result;
   });
```

---

## 6. Configuration {#configuration}

```json
// appsettings.json
{
  "ConnectionStrings": { "Default": "Server=...;Database=MyApp" },
  "Jwt": { "Secret": "...", "Issuer": "myapp", "ExpireMinutes": 60 },
  "Smtp": { "Host": "smtp.example.com", "Port": 587 }
}
```

```csharp
// Access configuration
var connStr = builder.Configuration.GetConnectionString("Default");
var jwtSecret = builder.Configuration["Jwt:Secret"];

// Strongly-typed options
public class JwtOptions
{
    public string Secret { get; set; } = "";
    public string Issuer { get; set; } = "";
    public int ExpireMinutes { get; set; } = 60;
}

services.Configure<JwtOptions>(config.GetSection("Jwt"));

// Environment-based overrides: appsettings.Production.json, env vars, secrets
// Env var: Jwt__Secret=myvalue (double underscore = colon)
```

---

## 7. Authentication & Authorization {#auth}

### JWT Authentication
```csharp
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuerSigningKey = true,
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret)),
            ValidateIssuer = true,
            ValidIssuer = jwtOptions.Issuer,
            ValidateAudience = false,
            ClockSkew = TimeSpan.Zero
        };
    });

// Policy-based authorization
builder.Services.AddAuthorizationBuilder()
    .AddPolicy("AdminOnly", p => p.RequireRole("Admin"))
    .AddPolicy("MinAge18", p => p.RequireClaim("age", "18"));

// Apply to endpoints
app.MapGet("/admin", () => "Admin only").RequireAuthorization("AdminOnly");
app.MapGet("/public", () => "Anyone").AllowAnonymous();

// Token generation
var claims = new[] {
    new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
    new Claim(ClaimTypes.Role, user.Role)
};
var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret));
var token = new JwtSecurityToken(
    issuer: issuer,
    claims: claims,
    expires: DateTime.UtcNow.AddMinutes(60),
    signingCredentials: new SigningCredentials(key, SecurityAlgorithms.HmacSha256)
);
```

### Data Protection
```csharp
// For cookie encryption, CSRF tokens, etc.
builder.Services.AddDataProtection()
    .PersistKeysToFileSystem(new DirectoryInfo("/keys"))
    .SetApplicationName("MyApp");
```

---

## 8. Blazor {#blazor}

```csharp
// Program.cs for Blazor Web App
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents()    // SignalR-based
    .AddInteractiveWebAssemblyComponents(); // WASM

// Component (.razor file)
@page "/counter"
@rendermode InteractiveServer

<h1>Counter: @count</h1>
<button @onclick="Increment">Click me</button>

@code {
    private int count = 0;
    private void Increment() => count++;
}

// Data binding
<input @bind="searchTerm" @bind:event="oninput" />

// Dependency injection in components
@inject IUserService UserService

// Lifecycle
protected override async Task OnInitializedAsync()
{
    users = await UserService.GetAllAsync();
}
```

---

## 9. SignalR & gRPC {#realtime}

### SignalR (Real-time)
```csharp
// Hub
public class ChatHub : Hub
{
    public async Task SendMessage(string user, string message) =>
        await Clients.All.SendAsync("ReceiveMessage", user, message);
        
    public async Task JoinGroup(string groupName) =>
        await Groups.AddToGroupAsync(Context.ConnectionId, groupName);
}

// Setup
builder.Services.AddSignalR();
app.MapHub<ChatHub>("/chathub");
```

### gRPC
```csharp
// .proto file defines the contract
// service Greeter { rpc SayHello (HelloRequest) returns (HelloReply); }

// Implementation
public class GreeterService : Greeter.GreeterBase
{
    public override Task<HelloReply> SayHello(HelloRequest request, ServerCallContext context) =>
        Task.FromResult(new HelloReply { Message = $"Hello {request.Name}" });
}

builder.Services.AddGrpc();
app.MapGrpcService<GreeterService>();
```

---

## 10. Testing {#testing}

```csharp
// Integration testing with WebApplicationFactory
public class ApiTests(WebApplicationFactory<Program> factory) 
    : IClassFixture<WebApplicationFactory<Program>>
{
    [Fact]
    public async Task GetUsers_ReturnsOk()
    {
        var client = factory.CreateClient();
        var response = await client.GetAsync("/api/users");
        response.EnsureSuccessStatusCode();
        
        var users = await response.Content.ReadFromJsonAsync<List<UserDto>>();
        Assert.NotNull(users);
    }
}

// Custom factory for test overrides
var factory = new WebApplicationFactory<Program>()
    .WithWebHostBuilder(builder =>
        builder.ConfigureServices(services =>
        {
            services.RemoveAll<IUserService>();
            services.AddScoped(_ => mockUserService);
        }));
```

---

## 11. Deployment {#deployment}

```dockerfile
# Multi-stage Dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY . .
RUN dotnet publish -c Release -o /app

FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /app .
EXPOSE 8080
ENTRYPOINT ["dotnet", "MyApp.dll"]
```

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports: ["8080:8080"]
    environment:
      - ASPNETCORE_ENVIRONMENT=Production
      - ConnectionStrings__Default=Server=db;...
    depends_on: [db]
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: myapp
      POSTGRES_PASSWORD: secret
```

**Key deployment concerns:**
- Use environment variables for secrets (never commit secrets)
- Configure health check endpoints: `app.MapHealthChecks("/health")`
- Set `ASPNETCORE_ENVIRONMENT=Production` to disable developer exception pages
- Configure Kestrel limits for production (`MaxRequestBodySize`, timeouts)
- Use HTTPS with proper certificate management
