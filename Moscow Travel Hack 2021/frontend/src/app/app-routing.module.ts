import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { PlaceDetailComponent } from './place-detail/place-detail.component';
import { PlacesComponent } from './places/places.component';

const routes: Routes = [
  { path: 'places',  component: PlacesComponent },
  { path: 'place/:id', component: PlaceDetailComponent }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
