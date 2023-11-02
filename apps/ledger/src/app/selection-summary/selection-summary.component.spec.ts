import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SelectionSummaryComponent } from './selection-summary.component';

describe('SelectionSummaryComponent', () => {
  let component: SelectionSummaryComponent;
  let fixture: ComponentFixture<SelectionSummaryComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ SelectionSummaryComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SelectionSummaryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
