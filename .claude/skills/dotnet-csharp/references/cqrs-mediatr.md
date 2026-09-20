# CQRS Pattern with MediatR

Source: https://www.milanjovanovic.tech/blog/cqrs-pattern-with-mediatr

## What is CQRS?

CQRS stands for **Command Query Responsibility Segregation**. It separates the models used for reading and updating data. Benefits include complexity management, improved performance, scalability, and security.

The standard CRUD approach uses the same model for reads and writes — simple and fine for basic apps. In complex applications it becomes hard to maintain: writes may carry heavy business logic and validation, while reads need many different query shapes.

### CQS vs CQRS

**CQS (Command Query Separation)** — a method-level principle by Bertrand Meyer:
- **Commands**: change state, return nothing
- **Queries**: return a value, no side effects

**CQRS** is the architectural evolution of CQS — applied at the system/service level rather than the method level.

---

## Flavors of CQRS

| Approach | Write Side | Read Side | Notes |
|----------|-----------|-----------|-------|
| Logical separation | Same DB | Same DB | Lowest complexity, good starting point |
| Physical separation | SQL DB | NoSQL (RavenDB, etc.) | Better read performance |
| Event sourcing | Event store | Projection DB / Redis | Highest complexity, full audit trail |

> Eventual consistency is introduced when you physically separate databases — factor in synchronization failure handling.

---

## Implementing CQRS with MediatR

MediatR implements the **mediator pattern** to decouple the in-process sending of messages from their handling. It routes commands and queries to the correct handler automatically.

### Setup

```bash
dotnet add package MediatR
```

### Custom ICommand / IQuery Abstractions

Extend MediatR's `IRequest` to make commands and queries explicit in your codebase:

```csharp
// Marker interfaces for clarity
public interface ICommand : IRequest<Result> { }
public interface ICommand<TResponse> : IRequest<Result<TResponse>> { }

public interface IQuery<TResponse> : IRequest<Result<TResponse>> { }

// Handler interfaces
public interface ICommandHandler<TCommand> : IRequestHandler<TCommand, Result>
    where TCommand : ICommand { }

public interface ICommandHandler<TCommand, TResponse> : IRequestHandler<TCommand, Result<TResponse>>
    where TCommand : ICommand<TResponse> { }

public interface IQueryHandler<TQuery, TResponse> : IRequestHandler<TQuery, Result<TResponse>>
    where TQuery : IQuery<TResponse> { }
```

### Registration

```csharp
builder.Services.AddMediatR(cfg =>
    cfg.RegisterServicesFromAssemblyContaining<Program>());
```

---

## Command Side — EF Core + Rich Domain Model

Commands encapsulate business logic. Use EF Core to load an aggregate, run domain logic, and persist changes.

### Controller (using ISender)

```csharp
[ApiController]
[Route("api/bookings")]
public class BookingsController : ControllerBase
{
    private readonly ISender _sender;

    public BookingsController(ISender sender) => _sender = sender;

    [HttpPut("{id}/confirm")]
    public async Task<IActionResult> ConfirmBooking(Guid id, CancellationToken ct)
    {
        var command = new ConfirmBookingCommand(id);
        var result = await _sender.Send(command, ct);

        return result.IsFailure
            ? BadRequest(result.Error)
            : NoContent();
    }
}
```

> Prefer injecting `ISender` over `IMediator` — it's the minimal interface needed for sending requests.

### Command + Handler

```csharp
public record ConfirmBookingCommand(Guid BookingId) : ICommand;

internal sealed class ConfirmBookingCommandHandler : ICommandHandler<ConfirmBookingCommand>
{
    private readonly IBookingRepository _bookingRepository;
    private readonly IDateTimeProvider _dateTimeProvider;
    private readonly IUnitOfWork _unitOfWork;

    public ConfirmBookingCommandHandler(
        IBookingRepository bookingRepository,
        IDateTimeProvider dateTimeProvider,
        IUnitOfWork unitOfWork)
    {
        _bookingRepository = bookingRepository;
        _dateTimeProvider = dateTimeProvider;
        _unitOfWork = unitOfWork;
    }

    public async Task<Result> Handle(ConfirmBookingCommand request, CancellationToken ct)
    {
        var booking = await _bookingRepository.GetByIdAsync(request.BookingId, ct);
        if (booking is null)
            return Result.Failure(BookingErrors.NotFound);

        var result = booking.Confirm(_dateTimeProvider.UtcNow);
        if (result.IsFailure)
            return result;

        await _unitOfWork.SaveChangesAsync(ct);
        return Result.Success();
    }
}
```

---

## Query Side — Dapper + Raw SQL

Queries are all about **performance** — minimize indirection. Dapper with raw SQL is an excellent choice. EF Core projections with `AsNoTracking()` also work well.

```csharp
public record SearchApartmentsQuery(DateOnly StartDate, DateOnly EndDate)
    : IQuery<IReadOnlyList<ApartmentResponse>>;

internal sealed class SearchApartmentsQueryHandler
    : IQueryHandler<SearchApartmentsQuery, IReadOnlyList<ApartmentResponse>>
{
    private static readonly int[] ActiveBookingStatuses =
    [
        (int)BookingStatus.Reserved,
        (int)BookingStatus.Confirmed,
        (int)BookingStatus.Completed
    ];

    private readonly ISqlConnectionFactory _sqlConnectionFactory;

    public SearchApartmentsQueryHandler(ISqlConnectionFactory sqlConnectionFactory) =>
        _sqlConnectionFactory = sqlConnectionFactory;

    public async Task<Result<IReadOnlyList<ApartmentResponse>>> Handle(
        SearchApartmentsQuery request, CancellationToken ct)
    {
        if (request.StartDate > request.EndDate)
            return new List<ApartmentResponse>();

        using var connection = _sqlConnectionFactory.CreateConnection();

        const string sql = """
            SELECT
                a.id AS Id,
                a.name AS Name,
                a.price_amount AS Price,
                a.price_currency AS Currency,
                a.address_country AS Country,
                a.address_city AS City,
                a.address_street AS Street
            FROM apartments AS a
            WHERE NOT EXISTS (
                SELECT 1 FROM bookings AS b
                WHERE b.apartment_id = a.id
                  AND b.duration_start <= @EndDate
                  AND b.duration_end >= @StartDate
                  AND b.status = ANY(@ActiveBookingStatuses)
            )
            """;

        var apartments = await connection.QueryAsync<ApartmentResponse>(
            sql,
            new { request.StartDate, request.EndDate, ActiveBookingStatuses });

        return apartments.ToList();
    }
}
```

### ISqlConnectionFactory

```csharp
public interface ISqlConnectionFactory
{
    IDbConnection CreateConnection();
}

public class SqlConnectionFactory(string connectionString) : ISqlConnectionFactory
{
    public IDbConnection CreateConnection()
    {
        var connection = new NpgsqlConnection(connectionString); // or SqlConnection
        connection.Open();
        return connection;
    }
}

// Registration
services.AddSingleton<ISqlConnectionFactory>(_ =>
    new SqlConnectionFactory(config.GetConnectionString("Default")!));
```

---

## Pipeline Behaviors (Cross-Cutting Concerns)

`IPipelineBehavior<TRequest, TResponse>` wraps every request — ideal for validation, logging, caching, and transactions.

### Validation with FluentValidation

```csharp
public class ValidationBehavior<TRequest, TResponse>(
    IEnumerable<IValidator<TRequest>> validators)
    : IPipelineBehavior<TRequest, TResponse>
    where TRequest : IBaseCommand
{
    public async Task<TResponse> Handle(
        TRequest request, RequestHandlerDelegate<TResponse> next, CancellationToken ct)
    {
        if (!validators.Any()) return await next();

        var context = new ValidationContext<TRequest>(request);
        var failures = validators
            .Select(v => v.Validate(context))
            .SelectMany(r => r.Errors)
            .Where(f => f != null)
            .ToList();

        if (failures.Count != 0)
            throw new ValidationException(failures);

        return await next();
    }
}

// Registration
services.AddTransient(typeof(IPipelineBehavior<,>), typeof(ValidationBehavior<,>));
services.AddValidatorsFromAssemblyContaining<Program>();
```

### Logging Behavior

```csharp
public class LoggingBehavior<TRequest, TResponse>(ILogger<LoggingBehavior<TRequest, TResponse>> logger)
    : IPipelineBehavior<TRequest, TResponse>
    where TRequest : IBaseCommand
{
    public async Task<TResponse> Handle(
        TRequest request, RequestHandlerDelegate<TResponse> next, CancellationToken ct)
    {
        logger.LogInformation("Handling {RequestName}", typeof(TRequest).Name);
        var response = await next();
        logger.LogInformation("Handled {RequestName}", typeof(TRequest).Name);
        return response;
    }
}
```

---

## Key Decisions Summary

| Concern | Write (Command) Side | Read (Query) Side |
|---------|---------------------|-------------------|
| ORM | EF Core + rich domain model | Dapper / EF projections |
| Pattern | Repository + Unit of Work | Direct SQL or thin read model |
| Focus | Correctness + business rules | Performance + flexibility |
| Return type | `Result` (no data) | `Result<T>` with DTO |

---

## When to Use CQRS

✅ Complex domain with rich business logic  
✅ Read patterns differ significantly from write patterns  
✅ Different scaling needs for reads vs writes  
✅ Teams working on reads and writes independently  

⚠️ Avoid for simple CRUD apps — overhead outweighs benefits  
⚠️ Physical DB separation adds eventual consistency complexity — only add when needed
