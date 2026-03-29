// P118: Scala v2 - Akka-based Actor System
import akka.actor._

case class Unit(id: Int, health: Float, damage: Float, x: Float, y: Float)
case class CalculatePower()
case class FindThreats()

class BattleSimulator extends Actor {
    var units: List[Unit] = List()
    
    def receive: Receive = {
        case u: Unit => units = units :+ u
        case CalculatePower() => 
            val power = units.map(u => u.health * u.damage).sum / 100.0f
            sender() ! power
        case FindThreats() =>
            val threats = units.map { u =>
                val nearby = units.count(e => e.id != u.id && distance(u, e) < 50f)
                (u.id, nearby * 10f)
            }.toMap
            sender() ! threats
    }
    
    def distance(a: Unit, b: Unit): Float = {
        val dx = a.x - b.x
        val dy = a.y - b.y
        Math.sqrt(dx*dx + dy*dy).toFloat
    }
}

object Main extends App {
    val system = ActorSystem("SC2Game")
    val sim = system.actorOf(Props[BattleSimulator](), "battleSim")
    sim ! Unit(1, 40, 5, 10, 10)
    sim ! CalculatePower()
}
