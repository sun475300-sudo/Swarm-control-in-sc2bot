// P90: C# - .NET Integration Module
// StarCraft II AI Bot - .NET Core Backend Integration

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.OpenApi.Models;
using Grpc.Net.Client;
using Google.Protobuf;

namespace WickedBot.Api
{
    public class Startup
    {
        public Startup(IConfiguration configuration)
        {
            Configuration = configuration;
        }

        public IConfiguration Configuration { get; }

        public void ConfigureServices(IServiceCollection services)
        {
            services.AddControllers();
            services.AddSwaggerGen(c =>
            {
                c.SwaggerDoc("v1", new OpenApiInfo { Title = "Wicked Bot API", Version = "v1" });
            });

            services.AddSingleton<IGameEngine, GameEngine>();
            services.AddSingleton<IAnalyticsService, AnalyticsService>();
            services.AddHostedService<GameLoopService>();

            services.AddGrpcClient<BotGrpc.BotGrpcClient>(options =>
            {
                options.Address = new Uri("http://localhost:5001");
            });
        }

        public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
        {
            if (env.IsDevelopment())
            {
                app.UseDeveloperExceptionPage();
                app.UseSwagger();
                app.UseSwaggerUI(c => c.SwaggerEndpoint("/swagger/v1/swagger.json", "Wicked Bot API"));
            }

            app.UseRouting();
            app.UseAuthorization();
            app.UseEndpoints(endpoints =>
            {
                endpoints.MapControllers();
            });
        }
    }

    public class Program
    {
        public static void Main(string[] args)
        {
            CreateHostBuilder(args).Build().Run();
        }

        public static IHostBuilder CreateHostBuilder(string[] args) =>
            Host.CreateDefaultBuilder(args)
                .ConfigureWebHostDefaults(webBuilder =>
                {
                    webBuilder.UseStartup<Startup>();
                });
    }

    public interface IGameEngine
    {
        Task<GameState> GetGameStateAsync();
        Task<bool> ExecuteCommandAsync(BotCommand command);
        Task<List<Unit>> GetUnitsAsync(UnitFilter filter);
    }

    public class GameEngine : IGameEngine
    {
        private readonly ILogger<GameEngine> _logger;
        private readonly GameContext _context;

        public GameEngine(ILogger<GameEngine> logger)
        {
            _logger = logger;
            _context = new GameContext();
        }

        public async Task<GameState> GetGameStateAsync()
        {
            return await Task.Run(() =>
            {
                return new GameState
                {
                    MapName = _context.CurrentMap,
                    GameTime = _context.ElapsedFrames / 22.4,
                    PlayerRace = Race.Zerg,
                    EnemyRace = _context.EnemyRace,
                    PlayerUnits = _context.Units.Where(u => u.Owner == Player.Self).ToList(),
                    EnemyUnits = _context.Units.Where(u => u.Owner == Player.Enemy).ToList(),
                    Resources = new Resources
                    {
                        Minerals = _context.Minerals,
                        Vespene = _context.Vespene,
                        SupplyUsed = _context.SupplyUsed,
                        SupplyCap = _context.SupplyCap
                    }
                };
            });
        }

        public async Task<bool> ExecuteCommandAsync(BotCommand command)
        {
            _logger.LogInformation($"Executing command: {command.Type}");
            
            return await Task.Run(() =>
            {
                return command.Type switch
                {
                    CommandType.Train => ExecuteTrain(command.UnitType),
                    CommandType.Build => ExecuteBuild(command.UnitType, command.Position),
                    CommandType.Attack => ExecuteAttack(command.Position),
                    CommandType.Defend => ExecuteDefend(command.Position),
                    CommandType.Expand => ExecuteExpand(),
                    _ => false
                };
            });
        }

        public async Task<List<Unit>> GetUnitsAsync(UnitFilter filter)
        {
            return await Task.Run(() =>
            {
                var units = _context.Units.AsEnumerable();

                if (filter.Owner.HasValue)
                    units = units.Where(u => u.Owner == filter.Owner.Value);

                if (filter.UnitTypes?.Any() == true)
                    units = units.Where(u => filter.UnitTypes.Contains(u.Type));

                if (filter.MinSupply > 0)
                    units = units.Where(u => u.SupplyCost >= filter.MinSupply);

                return units.ToList();
            });
        }

        private bool ExecuteTrain(UnitType type)
        {
            var cost = GetUnitCost(type);
            if (_context.Minerals >= cost.Minerals && _context.Vespene >= cost.Vespene)
            {
                _context.Minerals -= cost.Minerals;
                _context.Vespene -= cost.Vespene;
                return true;
            }
            return false;
        }

        private bool ExecuteBuild(UnitType type, Position? pos)
        {
            return ExecuteTrain(type);
        }

        private bool ExecuteAttack(Position target)
        {
            _logger.LogInformation($"Attack command at ({target.X}, {target.Y})");
            return true;
        }

        private bool ExecuteDefend(Position target)
        {
            _logger.LogInformation($"Defend command at ({target.X}, {target.Y})");
            return true;
        }

        private bool ExecuteExpand()
        {
            return true;
        }

        private Cost GetUnitCost(UnitType type)
        {
            return type switch
            {
                UnitType.Drone => new Cost { Minerals = 50, Vespene = 0 },
                UnitType.Zergling => new Cost { Minerals = 25, Vespene = 0 },
                UnitType.Roach => new Cost { Minerals = 75, Vespene = 25 },
                UnitType.Hydralisk => new Cost { Minerals = 100, Vespene = 50 },
                UnitType.Mutalisk => new Cost { Minerals = 100, Vespene = 100 },
                UnitType.Overlord => new Cost { Minerals = 100, Vespene = 0 },
                UnitType.Ultralisk => new Cost { Minerals = 300, Vespene = 200 },
                _ => new Cost { Minerals = 50, Vespene = 0 }
            };
        }
    }

    public class GameState
    {
        public string MapName { get; set; }
        public double GameTime { get; set; }
        public Race PlayerRace { get; set; }
        public Race EnemyRace { get; set; }
        public List<Unit> PlayerUnits { get; set; } = new();
        public List<Unit> EnemyUnits { get; set; } = new();
        public Resources Resources { get; set; }
    }

    public class Unit
    {
        public int Id { get; set; }
        public UnitType Type { get; set; }
        public Position Position { get; set; }
        public Player Owner { get; set; }
        public double Health { get; set; }
        public double MaxHealth { get; set; }
        public int SupplyCost { get; set; }
    }

    public class Position
    {
        public float X { get; set; }
        public float Y { get; set; }
    }

    public class Resources
    {
        public int Minerals { get; set; }
        public int Vespene { get; set; }
        public int SupplyUsed { get; set; }
        public int SupplyCap { get; set; }
    }

    public class Cost
    {
        public int Minerals { get; set; }
        public int Vespene { get; set; }
    }

    public enum Race { Zerg, Terran, Protoss, Random }
    public enum Player { Self, Enemy }
    public enum UnitType { Drone, Zergling, Roach, Hydralisk, Mutalisk, Overlord, Queen, Ultralisk, BroodLord }
    public enum CommandType { Train, Build, Attack, Defend, Expand, Research }

    public class BotCommand
    {
        public CommandType Type { get; set; }
        public UnitType? UnitType { get; set; }
        public Position? Position { get; set; }
    }

    public class UnitFilter
    {
        public Player? Owner { get; set; }
        public List<UnitType> UnitTypes { get; set; }
        public int MinSupply { get; set; }
    }

    public interface IAnalyticsService
    {
        Task<AnalyticsReport> GenerateReportAsync(DateTime from, DateTime to);
    }

    public class AnalyticsService : IAnalyticsService
    {
        public async Task<AnalyticsReport> GenerateReportAsync(DateTime from, DateTime to)
        {
            return await Task.Run(() => new AnalyticsReport
            {
                TotalGames = 100,
                WinRate = 0.42,
                AvgGameDuration = 12.5,
                MostPlayedBuild = "RoachHydralisk",
                BestMatchup = "ZergvZerg"
            });
        }
    }

    public class AnalyticsReport
    {
        public int TotalGames { get; set; }
        public double WinRate { get; set; }
        public double AvgGameDuration { get; set; }
        public string MostPlayedBuild { get; set; }
        public string BestMatchup { get; set; }
    }

    public class GameLoopService : BackgroundService
    {
        private readonly ILogger<GameLoopService> _logger;
        private readonly IGameEngine _engine;

        public GameLoopService(ILogger<GameLoopService> logger, IGameEngine engine)
        {
            _logger = logger;
            _engine = engine;
        }

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            while (!stoppingToken.IsCancellationRequested)
            {
                var state = await _engine.GetGameStateAsync();
                _logger.LogDebug($"Game time: {state.GameTime:F1}s, Units: {state.PlayerUnits.Count}");
                await Task.Delay(100, stoppingToken);
            }
        }
    }
}
