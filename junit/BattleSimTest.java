import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class BattleSimTest {
    @Test
    public void testCalculateSwarmDamage() {
        assertEquals(50, calculateSwarmDamage(10));
    }
}
