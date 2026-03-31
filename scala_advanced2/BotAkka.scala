// Phase 547: Scala Advanced 2 — Akka Actor Model
// SC2 Bot with Akka typed actors + streams

package sc2bot.akka

import scala.concurrent.{Future, ExecutionContext}
import scala.concurrent.duration._
import scala.util.{Success, Failure, Random}

// ─────────────────────────────────────────────
// Domain models
// ─────────────────────────────────────────────

enum Race: Zerg, Terran, Protoss

enum UnitType:
  case Drone, Zergling, Roach, Hydralisk, Mutalisk, Ultralisk, Queen, Overlord

case class Resources(
  minerals: Int,
  gas: Int,
  supply: Int,
  maxSupply: Int
):
  def canAfford(m: Int, g: Int): Boolean = minerals >= m && gas >= g
  def supplyFull: Boolean = supply >= maxSupply - 1
  def use(m: Int, g: Int, s: Int): Resources =
    copy(minerals = minerals - m, gas = gas - g, supply = supply + s)
  def expandSupply(n: Int): Resources = copy(maxSupply = maxSupply + n)

case class ArmyState(mySupply: Int, enemySupply: Int, threatLevel: Double):
  def underThreat: Boolean = threatLevel > 0.6

case class GameState(
  resources: Resources,
  army: ArmyState,
  workers: Int,
  frame: Int,
  hatcheries: Int,
  enemyRace: Race,
):
  def phase: String = frame match
    case f if f < 1344 => "Opening"
    case f if f < 3360 => "EarlyGame"
    case f if f < 6720 => "MidGame"
    case _             => "LateGame"

object GameState:
  def initial(race: Race = Race.Terran): GameState = GameState(
    resources = Resources(50, 0, 12, 14),
    army      = ArmyState(0, 0, 0.0),
    workers   = 12,
    frame     = 0,
    hatcheries = 1,
    enemyRace = race,
  )

// ─────────────────────────────────────────────
// Actions
// ─────────────────────────────────────────────

sealed trait Action
case class TrainUnit(unit: UnitType)       extends Action
case class BuildStructure(name: String)    extends Action
case object Expand                         extends Action
case class AttackMove(x: Float, y: Float)  extends Action
case object Defend                         extends Action
case object Wait                           extends Action

// ─────────────────────────────────────────────
// Akka Actor messages (without Akka dependency)
// ─────────────────────────────────────────────

sealed trait BotMessage
case class Tick(frames: Int)              extends BotMessage
case class StateQuery()                   extends BotMessage
case class StateResponse(s: GameState)    extends BotMessage
case class TrainRequest(u: UnitType)      extends BotMessage
case class ExpandRequest()                extends BotMessage

// ─────────────────────────────────────────────
// Strategy engine
// ─────────────────────────────────────────────

val unitCosts: Map[UnitType, (Int, Int, Int)] = Map(
  UnitType.Drone     -> (50, 0, 1),
  UnitType.Zergling  -> (25, 0, 1),
  UnitType.Roach     -> (75, 25, 2),
  UnitType.Hydralisk -> (100, 50, 2),
  UnitType.Mutalisk  -> (100, 100, 2),
  UnitType.Queen     -> (150, 0, 2),
  UnitType.Overlord  -> (100, 0, 0),
)

def decide(s: GameState): Action =
  val res = s.resources
  if s.army.underThreat then Defend
  else if res.supplyFull && res.canAfford(100, 0) then TrainUnit(UnitType.Overlord)
  else if s.workers < 22 && res.canAfford(50, 0)  then TrainUnit(UnitType.Drone)
  else if res.minerals >= 300 && s.hatcheries < 3  then Expand
  else s.enemyRace match
    case Race.Terran  if res.canAfford(100, 50) => TrainUnit(UnitType.Hydralisk)
    case Race.Protoss if res.canAfford(75, 25)  => TrainUnit(UnitType.Roach)
    case _            if res.canAfford(25, 0)   => TrainUnit(UnitType.Zergling)
    case _                                      => Wait

def tick(s: GameState): GameState =
  val income = s.workers * 8 / 10
  s.copy(
    resources = s.resources.copy(minerals = s.resources.minerals + income),
    frame     = s.frame + 1,
    army      = s.army.copy(threatLevel = math.min(1.0, s.army.threatLevel + 0.0001)),
  )

def applyAction(s: GameState, action: Action): GameState = action match
  case TrainUnit(UnitType.Drone) if s.resources.canAfford(50, 0) =>
    s.copy(resources = s.resources.use(50, 0, 1), workers = s.workers + 1)
  case TrainUnit(u) =>
    unitCosts.get(u) match
      case Some((m, g, sup)) if s.resources.canAfford(m, g) =>
        val newArmy = if u == UnitType.Overlord
          then s.army
          else s.army.copy(mySupply = s.army.mySupply + sup)
        val newRes = if u == UnitType.Overlord
          then s.resources.use(m, g, 0).expandSupply(8)
          else s.resources.use(m, g, sup)
        s.copy(resources = newRes, army = newArmy)
      case _ => s
  case Expand if s.resources.canAfford(300, 0) =>
    s.copy(
      resources  = s.resources.use(300, 0, 0),
      hatcheries = s.hatcheries + 1,
      workers    = s.workers + 4,
    )
  case _ => s

def step(s: GameState): GameState = applyAction(tick(s), decide(tick(s)))

// ─────────────────────────────────────────────
// Simulated Akka-style actor (without runtime)
// ─────────────────────────────────────────────

class BotActor(initialState: GameState):
  private var state: GameState = initialState
  private val inbox: collection.mutable.Queue[BotMessage] = collection.mutable.Queue.empty

  def send(msg: BotMessage): Unit = inbox.enqueue(msg)

  def process(): Unit =
    while inbox.nonEmpty do
      inbox.dequeue() match
        case Tick(n) =>
          for _ <- 1 to n do state = step(state)
        case StateQuery() =>
          println(s"  State: ${state.phase} | frame=${state.frame} minerals=${state.resources.minerals}")
        case TrainRequest(u) =>
          state = applyAction(state, TrainUnit(u))
        case ExpandRequest() =>
          state = applyAction(state, Expand)
        case _ =>

  def getState: GameState = state

// ─────────────────────────────────────────────
// Functional streams simulation
// ─────────────────────────────────────────────

def stateStream(initial: GameState): LazyList[GameState] =
  LazyList.iterate(initial)(step)

def simulate(initial: GameState, frames: Int): GameState =
  stateStream(initial).drop(frames).head

def analyzeStream(initial: GameState, n: Int): Map[String, Double] =
  val states = stateStream(initial).take(n).toList
  Map(
    "avg_minerals" -> states.map(_.resources.minerals.toDouble).sum / n,
    "max_workers"  -> states.map(_.workers).max.toDouble,
    "max_army"     -> states.map(_.army.mySupply).max.toDouble,
    "expand_frame" -> states.find(_.hatcheries >= 2).map(_.frame.toDouble).getOrElse(-1.0),
  )

// ─────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────

@main def run(): Unit =
  println("Phase 547: Scala Advanced 2 — Akka Actor Model")

  // Actor simulation
  val actor = BotActor(GameState.initial(Race.Protoss))
  actor.send(Tick(500))
  actor.send(StateQuery())
  actor.send(Tick(500))
  actor.send(TrainRequest(UnitType.Roach))
  actor.send(StateQuery())
  actor.process()

  // Lazy stream analytics
  val metrics = analyzeStream(GameState.initial(Race.Terran), 2000)
  println("Metrics:")
  metrics.toSeq.sorted.foreach { (k, v) => println(f"  $k%-20s: $v%.1f") }

  // Final simulation
  val finalState = simulate(GameState.initial(Race.Zerg), 3000)
  println(s"\nFinal: frame=${finalState.frame} phase=${finalState.phase}")
