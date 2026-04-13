RSpec.describe BattleSim do
  it "calculates swarm damage" do
    expect(subject.calculate_swarm_damage(10)).to eq(50)
  end
end
