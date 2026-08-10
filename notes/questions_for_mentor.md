- আমাদের first paper-এর scope কি শুধু model comparison হবে, নাকি routing system evaluation-ও থাকবে?
- Heavy/Light ground truth কীভাবে define করলে academically valid হবে?
- Synthetic dataset কি যথেষ্ট, নাকি external dataset অবশ্যই দরকার?
- Human-reviewed retraining first paper-এ রাখব, নাকি future work করব?
- আমাদের target initially student conference, workshop, নাকি full conference paper হওয়া উচিত?
- Safe reroute and surge fairness এই paper-এ রাখব, নাকি separate paper হিসেবে রাখব?
- Mentor এবং team member-দের authorship order কীভাবে নির্ধারণ করা হবে?
# Questions for Mentor - Version 0.2

1. Do you approve the revised primary task: node-aware `service_time_ms` regression instead of fixed Heavy/Light classification?
2. Should the first paper include both model comparison and winner-model routing evaluation?
3. Is the proposed FinCluster reference processing pipeline academically acceptable if it is clearly presented as a reproducible simulation rather than a universal bank pipeline?
4. Which processing stages should be added, removed, or modified before measurement?
5. Which controlled Docker node profiles should be used for the pilot experiment?
6. Should node runtime conditions such as queue length and current CPU load be included in the first model, or should the first benchmark use static controlled profiles only?
7. Which exact PaySim source/version and license should be selected?
8. What transaction sample size is realistic for repeated execution across all node profiles?
9. Should optional node degradation and node failure remain in the first paper or become future work?
10. Is the proposed set of regression models sufficient and fair?
11. What paper type should be targeted first: student conference, workshop, short paper, or full conference paper?
12. How should author roles and author order be determined?
