from vcd import VCDWriter
import sys

def generate_vcd(num_cycles=20):
    with VCDWriter(sys.stdout, timescale='1 ns', date='today') as writer:
        # Register variables
        clk = writer.register_var('top', 'clk', 'reg', size=1)
        ff = []
        for i in range(5):
            ff.append(writer.register_var('top', f'ff{i}', 'reg', size=1))
        
        # Initial state
        writer.change(clk, 0, 0)  # Clock starts at 0
        writer.change(ff[0], 0, 1)  # First FF has the pulse
        for i in range(1, 5):
            writer.change(ff[i], 0, 0)
        
        # Simulate for specified number of cycles
        ff_state = [1, 0, 0, 0, 0]  # Current state of flip-flops
        
        for t in range(1, num_cycles * 2):
            # Toggle clock every time unit
            clock_value = t % 2
            writer.change(clk, t, clock_value)
            
            # On rising edge (clock transitions from 0 to 1)
            if clock_value == 1:
                # Shift the FF values
                ff_state = [ff_state[-1]] + ff_state[:-1]
                
                # Update all FFs
                for i in range(5):
                    writer.change(ff[i], t, ff_state[i])

if __name__ == '__main__':
    generate_vcd()
